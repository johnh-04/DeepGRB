"""
Standalone event localization test runner.
Loads a single candidate trigger, extracts multi-detector peak counts,
and fits coordinates via Particle Swarm Optimization (PSO).
"""

import logging
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gbm.data import HealPix, PosHist
from gbm.finder import ContinuousFtp
from gbm.plot import SkyPlot
from gbm.time import Met

from connections.utils.config import DATA_DIR, FOLD_BKG, FOLD_PRED
from models.loc.localization_class import Localization

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def run_positioning_example(
    start_month: str = "01-2014",
    end_month: str = "03-2014",
    day_file: str = "140127.csv",
    timestamp_event: str = "2014-01-27 05:21:12"
) -> None:
    """Performs PSO fitting and SkyPlot localization for a sample trigger timestamp."""
    frg_file = DATA_DIR / FOLD_PRED / f"frg_{start_month}_{end_month}.csv"
    bkg_file = DATA_DIR / FOLD_PRED / f"bkg_{start_month}_{end_month}.csv"
    event_day_file = DATA_DIR / FOLD_BKG / day_file

    if not frg_file.exists() or not event_day_file.exists():
        logging.error("Telemetry files missing for localization.")
        return

    df_frg = pd.read_csv(frg_file)
    df_bkg = pd.read_csv(bkg_file)
    df_event = pd.read_csv(event_day_file)

    met_event = Met(0).from_iso(timestamp_event.replace(" ", "T")).met
    df_bkg["met"] = df_frg["met"].values

    df_frg_bkg = pd.merge(df_event, df_bkg, how="left", on=["met"], suffixes=("_frg", "_bkg"))

    col_ra = np.sort([c for c in df_frg_bkg.columns if "_ra" in c and len(c) == 5 and "n" in c])
    col_dec = np.sort([c for c in df_frg_bkg.columns if "_dec" in c and len(c) == 6 and "n" in c])
    col_count_frg = np.sort([c for c in df_frg_bkg.columns if "_frg" in c and "n" in c and "_r0_" in c])
    col_count_bkg = np.sort([c for c in df_frg_bkg.columns if "_bkg" in c and "n" in c and "_r0_" in c])
    col_det = ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]

    df_frg_bkg[col_det] = df_frg_bkg[col_count_frg].values - df_frg_bkg[col_count_bkg].values

    # Restrict to +/- 500 s around target
    mask_window = (df_frg_bkg["met"] > met_event - 500) & (df_frg_bkg["met"] < met_event + 500)
    df_window = df_frg_bkg.loc[mask_window, col_det]

    if df_window.empty:
        logging.warning("No samples found around trigger timestamp.")
        return

    # Find peak index
    ind_max = df_window.max(axis=1).idxmax()
    logging.info(f"Event peak located at DataFrame index: {ind_max}")

    # Build 2D input arrays directly (avoiding deprecated DataFrame.append)
    ra_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_ra], dtype=np.float64) / 180.0 * np.pi)
    dec_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_dec], dtype=np.float64) / 180.0 * np.pi)
    cnt_frg = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_count_frg], dtype=np.float64))
    cnt_bkg = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_count_bkg], dtype=np.float64))

    loc = Localization(ra_vals, dec_vals, cnt_frg, cnt_bkg)
    res = loc.fit()
    _ = loc.fit_conf_int(250)
    mean, cov = loc.plot(plot_show=False)

    logging.info(f"PSO Fit Result: RA={res['ra']:.2f}, Dec={res['dec']:.2f}")

    # Download poshist and render SkyPlot
    tmp_dir = DATA_DIR / "tmp_pos"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        cont_finder = ContinuousFtp(met=int(round(met_event)))
        cont_finder.get_poshist(str(tmp_dir))
        pos_files = list(tmp_dir.glob("*.fits")) + list(tmp_dir.glob("*.fit"))
        if pos_files:
            poshist = PosHist.open(str(pos_files[0]))
            skyplot = SkyPlot()
            skyplot.add_poshist(poshist, trigtime=met_event)
            gauss_map = HealPix.from_gaussian(float(np.round(res["ra"])), float(np.round(res["dec"])), 10.0)
            skyplot.add_healpix(gauss_map)

            out_plot = DATA_DIR / "plots" / f"positioning_{timestamp_event.replace(':', '').replace(' ', '_')}.png"
            out_plot.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(out_plot, dpi=150, bbox_inches="tight")
            plt.close("all")
            logging.info(f"SkyPlot localization saved to: {out_plot}")
            pos_files[0].unlink(missing_ok=True)
    except Exception as e:
        logging.warning(f"Failed SkyPlot creation: {e}")


if __name__ == "__main__":
    run_positioning_example()