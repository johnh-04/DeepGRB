"""
Event localization (Crupi et al. 2023): at the bin of maximum residual inside the event,
the NaI residual counts are fitted with a cosine response (PSO), and a Monte Carlo of
Poisson-perturbed counts gives the error region. Orbital context (Earth, Sun, Fermi
position, McIlwain L) is taken from the local POSHIST file of the event day.
"""

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from gbm.coords import get_sun_loc
from gbm.data import HealPix, PosHist
from gbm.plot import SkyPlot

from models.loc.localization_class import Localization

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

NAI_DETS = ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]
LOC_COLUMNS = [
    "ra", "dec", "ra_montecarlo", "dec_montecarlo", "ra_std", "dec_std", "met_localisation",
    "ra_earth", "dec_earth", "earth_vis", "sun_vis", "ra_sun", "dec_sun", "l_galactic",
    "b_galactic", "lat_fermi", "lon_fermi", "alt_fermi", "l", "loc_range",
]
N_MONTECARLO = 250


def _poshist_file(poshist_dir: Path, day: str) -> Optional[Path]:
    files = sorted(poshist_dir.glob(f"glg_poshist_all_{day}_v*.fit"))
    return files[-1] if files else None


def localize_event(ev: pd.Series, frg: pd.DataFrame, bkg: pd.DataFrame, bkg_dir: Path, poshist_dir: Path,
                   pre_delay: float = 8.0, plot_path: Optional[Path] = None) -> dict:
    """Localizes one event row of events_table; returns the LOC_COLUMNS values."""
    trig = str(ev["trig_dets"]).split()
    ranges = [c.split("_")[1] for c in trig]
    # range with most triggered detectors; ties -> lowest range (upstream np.argmax)
    rng = ["r0", "r1", "r2"][int(np.argmax([ranges.count(r) for r in ("r0", "r1", "r2")]))]

    day = pd.Timestamp(ev["start_times"]).strftime("%y%m%d")
    daily = pd.read_csv(bkg_dir / f"{day}.csv", usecols=["met"] + [f"{d}_{k}" for d in NAI_DETS for k in ("ra", "dec")])

    win = (frg["met"] > ev["start_met"] - pre_delay) & (frg["met"] < ev["end_met"])
    cols = [f"{d}_{rng}" for d in NAI_DETS]
    resid = frg.loc[win, cols].to_numpy(dtype=float) - bkg.loc[win, cols].to_numpy(dtype=float)
    if not np.isfinite(resid).any():
        raise ValueError("no valid bins in the event window")
    i_peak = np.unravel_index(np.nanargmax(resid), resid.shape)[0]
    row = frg.loc[win].index[i_peak]
    met_loc = float(frg.at[row, "met"])

    point = daily.iloc[(daily["met"] - met_loc).abs().argmin()]
    ra_det = np.radians([point[f"{d}_ra"] for d in NAI_DETS])[None, :]
    dec_det = np.radians([point[f"{d}_dec"] for d in NAI_DETS])[None, :]
    cnt_frg = frg.loc[[row], cols].to_numpy(dtype=float)
    cnt_bkg = bkg.loc[[row], cols].to_numpy(dtype=float)

    loc = Localization(ra_det, dec_det, cnt_frg, cnt_bkg)
    res = loc.fit()
    loc.fit_conf_int(iters=N_MONTECARLO)
    mean, cov = loc.plot(plot_show=False)

    ph_file = _poshist_file(poshist_dir, day)
    if ph_file is None:
        raise FileNotFoundError(f"POSHIST missing for day {day}")
    ph = PosHist.open(str(ph_file))
    earth = ph.get_geocenter_radec(met_loc)
    sun = get_sun_loc(met_loc)
    gal = SkyCoord(res["ra"], res["dec"], unit="deg", frame="icrs").galactic

    if plot_path is not None:
        sky = SkyPlot()
        sky.add_poshist(ph, trigtime=met_loc)
        sky.add_healpix(HealPix.from_gaussian(float(np.round(res["ra"])), float(np.round(res["dec"])), 10.0))
        plt.title(f"{str(ev['start_times'])[:19]}  MET {met_loc:.2f}")
        plt.savefig(plot_path, bbox_inches="tight", dpi=120)
        plt.close("all")

    return {
        "ra": round(res["ra"], 2), "dec": round(res["dec"], 2),
        "ra_montecarlo": round(float(mean[0]), 2), "dec_montecarlo": round(float(mean[1]), 2),
        "ra_std": round(float(np.sqrt(cov[0][0])), 2), "dec_std": round(float(np.sqrt(cov[1][1])), 2),
        "met_localisation": met_loc,
        "ra_earth": float(earth[0]), "dec_earth": float(earth[1]),
        "earth_vis": bool(ph.location_visible(res["ra"], res["dec"], met_loc)),
        "sun_vis": bool(ph.get_sun_visibility(met_loc)),
        "ra_sun": float(sun[0]), "dec_sun": float(sun[1]),
        "l_galactic": float(gal.l.deg), "b_galactic": float(gal.b.deg),
        "lat_fermi": float(ph.get_latitude(met_loc)), "lon_fermi": float(ph.get_longitude(met_loc)),
        "alt_fermi": float(ph.get_altitude(met_loc)), "l": float(ph.get_mcilwain_l(met_loc)),
        "loc_range": rng,
    }


def localize(events_path: Path, frg_path: Path, bkg_path: Path, bkg_dir: Path, poshist_dir: Path,
             out_path: Path, plot_dir: Optional[Path] = None, seed: int = 42) -> pd.DataFrame:
    """Adds LOC_COLUMNS to every event and writes a new table (never overwrites)."""
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError(f"Refusing to overwrite {out_path}")
    np.random.seed(seed)
    events = pd.read_csv(events_path)
    frg = pd.read_csv(frg_path)
    bkg = pd.read_csv(bkg_path)
    if plot_dir is not None:
        Path(plot_dir).mkdir(parents=True, exist_ok=True)

    records = []
    for _, ev in events.iterrows():
        try:
            plot = Path(plot_dir) / f"event{int(ev['trig_ids'])}_loc.png" if plot_dir is not None else None
            rec = localize_event(ev, frg, bkg, Path(bkg_dir), Path(poshist_dir), plot_path=plot)
        except Exception as e:  # noqa: BLE001 - keep the event, mark the failure
            logging.error(f"Localization failed for event {ev['trig_ids']}: {e}")
            rec = {c: np.nan for c in LOC_COLUMNS}
        records.append(rec)
        logging.info(f"event {int(ev['trig_ids'])}: ra={rec['ra']} dec={rec['dec']}")
    out = pd.concat([events, pd.DataFrame(records, columns=LOC_COLUMNS)], axis=1)
    out.to_csv(out_path, index=False)
    return out
