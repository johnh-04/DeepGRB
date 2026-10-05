"""
Idempotent download of daily Fermi/GBM CSPEC and POSHIST files from HEASARC.

For every day of an inclusive date window the local folders are checked first;
only the files that are missing are requested, one detector at a time, with up
to `max_attempts` passes. A day that is already complete never opens an FTP
connection, so a second run downloads nothing.

Files are fetched into a temporary staging folder, validated (FITS checksums and
data readable) and only then moved into place. Existing files are never
rewritten: gbm-data-tools appends to an existing file of the same name, which
would corrupt it.
"""

import logging
import os
import re
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import pandas as pd
from astropy.io import fits

from connections.utils.config import DATA_DIR, FOLD_CSPEC_POS, FOLD_POSHIST
from utils.period import window_days

logger = logging.getLogger(__name__)

NAI_DETS = [f"n{d}" for d in "0123456789ab"]
BGO_DETS = ["b0", "b1"]
# preprocess.build_table requires all 14 CSPEC files of a day
CSPEC_DETS = NAI_DETS + BGO_DETS

PathLike = Union[str, Path]


def _cspec_re(day: str, det: str) -> re.Pattern:
    return re.compile(rf"glg_cspec_{det}_{day}_v\d{{2}}\.pha$")


def _poshist_re(day: str) -> re.Pattern:
    return re.compile(rf"glg_poshist_all_{day}_v\d{{2}}\.fit$")


def _present(folder: Path, pattern: re.Pattern) -> List[Path]:
    """Non-empty files in folder whose name matches pattern."""
    if not folder.exists():
        return []
    return [p for p in folder.iterdir() if pattern.match(p.name) and p.stat().st_size > 0]


def build_day_schedule(start_date: str, end_date: str) -> pd.DataFrame:
    """
    One row per day of the inclusive window.

    Columns: 'day' ('YYMMDD'), 'id' (alias of 'day', read by build_table),
    'date' ('YYYY-MM-DD'), 'tStart' (noon UTC, used to address the FTP folder).
    """
    days = window_days(start_date, end_date)
    dates = [pd.Timestamp(f"20{d[:2]}-{d[2:4]}-{d[4:]}") for d in days]
    return pd.DataFrame({
        "day": days,
        "id": days,
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "tStart": [d.strftime("%Y-%m-%dT12:00:00") for d in dates],
    })


def find_missing(day: str, cspec_dir: PathLike, poshist_dir: PathLike) -> Dict[str, object]:
    """Returns {'cspec': [missing detectors], 'poshist': True if POSHIST missing}. Empty files count as missing."""
    cspec_dir, poshist_dir = Path(cspec_dir), Path(poshist_dir)
    missing_dets = [det for det in CSPEC_DETS if not _present(cspec_dir, _cspec_re(day, det))]
    return {"cspec": missing_dets, "poshist": not _present(poshist_dir, _poshist_re(day))}


def missing_raw_days(days: List[str], cspec_dir: PathLike, poshist_dir: PathLike) -> List[str]:
    """Days ('YYMMDD') without all 14 CSPEC files or the POSHIST file; one directory listing per folder."""
    def names(folder: Path) -> set:
        if not folder.exists():
            return set()
        return {e.name for e in os.scandir(folder) if e.is_file() and e.stat().st_size > 0}
    cspec, poshist = names(Path(cspec_dir)), names(Path(poshist_dir))
    cspec_re = re.compile(r"glg_cspec_(\w\w)_(\d{6})_v\d{2}\.pha$")
    poshist_re = re.compile(r"glg_poshist_all_(\d{6})_v\d{2}\.fit$")
    have = {}
    for n in cspec:
        m = cspec_re.match(n)
        if m:
            have.setdefault(m.group(2), set()).add(m.group(1))
    pos_days = {m.group(1) for m in map(poshist_re.match, poshist) if m}
    return [d for d in days if not set(CSPEC_DETS) <= have.get(d, set()) or d not in pos_days]


def is_valid_fits(path: PathLike) -> bool:
    """True if every HDU opens, its data can be read and its CHECKSUM/DATASUM (when present) match."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with fits.open(str(path), checksum=True, memmap=False) as hdul:
                for hdu in hdul:
                    _ = hdu.data
        return True
    except Exception as e:  # noqa: BLE001 - any failure means the file is unusable
        logger.warning(f"Invalid FITS file {Path(path).name}: {e}")
        return False


def _install(staging: Path, pattern: re.Pattern, target_dir: Path) -> bool:
    """Moves validated staged files matching pattern into target_dir. Returns True if at least one was installed."""
    installed = False
    for f in sorted(staging.iterdir()):
        if not pattern.match(f.name):
            continue
        if is_valid_fits(f):
            os.replace(f, target_dir / f.name)
            installed = True
        else:
            f.unlink()
    return installed


def _download_day(row: pd.Series, missing: Dict[str, object], cspec_dir: Path, poshist_dir: Path,
                  ftp_factory: Callable) -> None:
    """Fetches only the missing files of one day through a staging folder."""
    day = row["day"]
    staging = Path(tempfile.mkdtemp(prefix=f".download_{day}_", dir=str(cspec_dir.parent)))
    try:
        try:
            ftp = ftp_factory(utc=row["tStart"])
        except Exception as e:  # noqa: BLE001 - network errors are retried on the next pass
            logger.error(f"[{day}] FTP connection failed: {e}")
            return

        for det in missing["cspec"]:
            try:
                ftp.get_cspec(str(staging), dets=[det], verbose=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[{day}] CSPEC {det} transfer failed: {e}")
            if not _install(staging, _cspec_re(day, det), cspec_dir):
                logger.warning(f"[{day}] CSPEC {det} not installed")

        if missing["poshist"]:
            try:
                ftp.get_poshist(str(staging), verbose=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[{day}] POSHIST transfer failed: {e}")
            if not _install(staging, _poshist_re(day), poshist_dir):
                logger.warning(f"[{day}] POSHIST not installed")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _describe(missing: Dict[str, object]) -> str:
    parts = [f"cspec:{','.join(missing['cspec'])}"] if missing["cspec"] else []
    if missing["poshist"]:
        parts.append("poshist")
    return " ".join(parts)


def download_days(
    start_date: str,
    end_date: str,
    cspec_dir: Optional[PathLike] = None,
    poshist_dir: Optional[PathLike] = None,
    max_attempts: int = 3,
    ftp_factory: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Ensures CSPEC (12 NaI + 2 BGO) and POSHIST files exist for every day of [start_date, end_date].

    :param start_date: first day, 'YYYY-MM-DD' (included)
    :param end_date: last day, 'YYYY-MM-DD' (included)
    :param cspec_dir: CSPEC folder (default data/cspec)
    :param poshist_dir: POSHIST folder (default data/poshist)
    :param max_attempts: download passes over the still-incomplete days
    :param ftp_factory: callable(utc=...) returning a ContinuousFtp-like object (injectable for tests)
    :return: schedule from build_day_schedule plus 'complete' (bool) and 'missing' (str) columns
    """
    cspec_dir = Path(cspec_dir or DATA_DIR / FOLD_CSPEC_POS)
    poshist_dir = Path(poshist_dir or DATA_DIR / FOLD_POSHIST)
    cspec_dir.mkdir(parents=True, exist_ok=True)
    poshist_dir.mkdir(parents=True, exist_ok=True)

    schedule = build_day_schedule(start_date, end_date)
    logger.info(f"Download window {start_date} -> {end_date}: {len(schedule)} days")

    for attempt in range(1, max_attempts + 1):
        pending = []
        for _, row in schedule.iterrows():
            missing = find_missing(row["day"], cspec_dir, poshist_dir)
            if missing["cspec"] or missing["poshist"]:
                pending.append((row, missing))
        if not pending:
            break
        if ftp_factory is None:
            # lazy import: gbm.finder logs into the HEASARC FTP server as soon as it is imported
            from gbm.finder import ContinuousFtp
            ftp_factory = ContinuousFtp
        logger.info(f"[attempt {attempt}/{max_attempts}] {len(pending)} incomplete day(s)")
        for row, missing in pending:
            logger.info(f"[{row['day']}] fetching {_describe(missing)}")
            _download_day(row, missing, cspec_dir, poshist_dir, ftp_factory)

    final = [find_missing(d, cspec_dir, poshist_dir) for d in schedule["day"]]
    schedule["missing"] = [_describe(m) for m in final]
    schedule["complete"] = schedule["missing"] == ""

    incomplete = schedule.loc[~schedule["complete"], ["day", "missing"]]
    if incomplete.empty:
        logger.info(f"All {len(schedule)} days complete (14 CSPEC + POSHIST).")
    else:
        for r in incomplete.itertuples():
            logger.warning(f"Day {r.day} still incomplete: {r.missing}")
    return schedule
