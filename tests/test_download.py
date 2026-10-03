"""Tests for the idempotent, per-file retrying downloader (docs/WORKING_RULES.md §5.6).

The FTP layer is replaced by a fake that writes small FITS files, so these
tests never touch the network.
"""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from astropy.io import fits

import connections.utils.config as cfg
from models.download_bkg import (
    CSPEC_DETS,
    build_day_schedule,
    download_days,
    download_spec,
    find_missing,
    is_valid_fits,
)


def _write_fits(path: Path, truncate: bool = False) -> None:
    fits.PrimaryHDU(data=np.arange(2880, dtype=np.int32)).writeto(path, checksum=True)
    if truncate:
        size = path.stat().st_size
        with open(path, "r+b") as f:
            f.truncate(size // 2)


def _populate_day(cspec_dir: Path, poshist_dir: Path, day: str, skip_dets=(), poshist=True) -> None:
    for det in CSPEC_DETS:
        if det not in skip_dets:
            _write_fits(cspec_dir / f"glg_cspec_{det}_{day}_v00.pha")
    if poshist:
        _write_fits(poshist_dir / f"glg_poshist_all_{day}_v01.fit")


class FakeFtp:
    """Mimics gbm.finder.ContinuousFtp for one day; records every request."""

    calls = []
    fail_once = set()  # detector names (or 'poshist') that fail on first request
    corrupt = set()  # detector names (or 'poshist') written truncated

    def __init__(self, utc=None, **_):
        FakeFtp.calls.append(("connect", utc))
        self.day = utc[2:4] + utc[5:7] + utc[8:10]

    def get_cspec(self, download_dir, dets=None, **_):
        for det in dets:
            FakeFtp.calls.append(("cspec", det))
            if det in FakeFtp.fail_once:
                FakeFtp.fail_once.discard(det)
                raise ConnectionError("simulated transfer error")
            _write_fits(Path(download_dir) / f"glg_cspec_{det}_{self.day}_v00.pha", truncate=det in FakeFtp.corrupt)

    def get_poshist(self, download_dir, **_):
        FakeFtp.calls.append(("poshist", None))
        if "poshist" in FakeFtp.fail_once:
            FakeFtp.fail_once.discard("poshist")
            raise ConnectionError("simulated transfer error")
        _write_fits(Path(download_dir) / f"glg_poshist_all_{self.day}_v01.fit", truncate="poshist" in FakeFtp.corrupt)

    @classmethod
    def reset(cls):
        cls.calls, cls.fail_once, cls.corrupt = [], set(), set()


def _no_network(*_, **__):
    raise AssertionError("FTP must not be contacted when data are complete")


class DownloadTestCase(unittest.TestCase):
    def setUp(self):
        FakeFtp.reset()
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.cspec = root / "cspec"
        self.poshist = root / "poshist"
        self.cspec.mkdir()
        self.poshist.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def run_download(self, start="2019-07-01", end="2019-07-01", **kw):
        kw.setdefault("ftp_factory", FakeFtp)
        return download_days(start, end, cspec_dir=self.cspec, poshist_dir=self.poshist, **kw)


class TestSchedule(unittest.TestCase):
    def test_schedule_has_explicit_day_column(self):
        df = build_day_schedule("2019-03-01", "2019-07-09")
        self.assertEqual(len(df), 131)
        self.assertIn("day", df.columns)
        self.assertEqual(df["day"].iloc[0], "190301")
        self.assertEqual(df["day"].iloc[-1], "190709")
        # 'id' is kept as an alias because build_table reads row['id']
        self.assertTrue((df["day"] == df["id"]).all())
        self.assertTrue(df["day"].str.fullmatch(r"\d{6}").all())


class TestFindMissing(DownloadTestCase):
    def test_reports_missing_detectors_and_poshist(self):
        _populate_day(self.cspec, self.poshist, "190701", skip_dets=("n3", "b1"), poshist=False)
        missing = find_missing("190701", self.cspec, self.poshist)
        self.assertEqual(missing["cspec"], ["n3", "b1"])
        self.assertTrue(missing["poshist"])

    def test_complete_day(self):
        _populate_day(self.cspec, self.poshist, "190701")
        self.assertEqual(find_missing("190701", self.cspec, self.poshist), {"cspec": [], "poshist": False})

    def test_empty_file_counts_as_missing(self):
        _populate_day(self.cspec, self.poshist, "190701")
        (self.cspec / "glg_cspec_n0_190701_v00.pha").write_bytes(b"")
        self.assertEqual(find_missing("190701", self.cspec, self.poshist)["cspec"], ["n0"])


class TestDownloadDays(DownloadTestCase):
    def test_complete_window_needs_no_network(self):
        for day in ("190701", "190702"):
            _populate_day(self.cspec, self.poshist, day)
        df = self.run_download("2019-07-01", "2019-07-02", ftp_factory=_no_network)
        self.assertTrue(df["complete"].all())

    def test_only_missing_files_are_requested(self):
        _populate_day(self.cspec, self.poshist, "190701", skip_dets=("n3",), poshist=False)
        df = self.run_download()
        requested = [c for c in FakeFtp.calls if c[0] != "connect"]
        self.assertEqual(requested, [("cspec", "n3"), ("poshist", None)])
        self.assertTrue(df["complete"].all())

    def test_transient_failure_is_retried_per_file(self):
        FakeFtp.fail_once = {"n5", "poshist"}
        df = self.run_download(max_attempts=2)
        self.assertTrue(df["complete"].all())
        self.assertEqual(find_missing("190701", self.cspec, self.poshist), {"cspec": [], "poshist": False})
        self.assertEqual(sum(1 for c in FakeFtp.calls if c == ("cspec", "n5")), 2)

    def test_second_run_downloads_nothing(self):
        self.run_download()
        FakeFtp.reset()
        df = self.run_download(ftp_factory=_no_network)
        self.assertTrue(df["complete"].all())

    def test_corrupted_download_is_rejected_and_not_moved(self):
        FakeFtp.corrupt = {"n7"}
        df = self.run_download(max_attempts=2)
        self.assertFalse(df["complete"].iloc[0])
        self.assertEqual(df["missing"].iloc[0], "cspec:n7")
        self.assertFalse(any(self.cspec.glob("*_n7_*")))
        # no staging leftovers next to the data folders
        self.assertEqual(sorted(p.name for p in self.cspec.parent.iterdir()), ["cspec", "poshist"])

    def test_existing_files_are_never_rewritten(self):
        _populate_day(self.cspec, self.poshist, "190701", skip_dets=("na",))
        kept = self.cspec / "glg_cspec_n0_190701_v00.pha"
        before = (kept.read_bytes(), kept.stat().st_mtime_ns)
        self.run_download()
        self.assertEqual((kept.read_bytes(), kept.stat().st_mtime_ns), before)


class TestIsValidFits(DownloadTestCase):
    def test_valid_and_truncated(self):
        good = self.cspec / "good.pha"
        bad = self.cspec / "bad.pha"
        _write_fits(good)
        _write_fits(bad, truncate=True)
        self.assertTrue(is_valid_fits(good))
        self.assertFalse(is_valid_fits(bad))


@unittest.skipUnless((cfg.DATA_DIR / "cspec").exists(), "production data folder not available")
class TestLegacyWrapperOnProductionData(unittest.TestCase):
    def test_month_wrapper_returns_day_column_without_network(self):
        # March-June 2019 are complete on disk: the wrapper must not touch FTP.
        df = download_spec("03-2019", "07-2019", ftp_factory=_no_network)
        self.assertEqual(len(df), 122)
        self.assertIn("day", df.columns)
        self.assertTrue(df["complete"].all())


if __name__ == "__main__":
    unittest.main()
