"""
Event visualizer and SkyPlot generator for candidate time intervals.
Plots multi-channel foreground vs background lightcurves and orbital sky orientation.
"""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Safe headless execution on HPC clusters
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gbm.data import PosHist
from gbm.finder import ContinuousFtp
from gbm.plot import SkyPlot
from connections.utils.config import DATA_DIR, FOLD_PRED

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def inspect_event_window(
    start_time_str: str = "2009-10-24 07:55:00",
    end_time_str: str = "2009-10-24 10:15:00",
    start_month: str = "09-2009",
    end_month: str = "12-2009",
    output_dir: Optional[Path] = None
) -> None:
    """
    Plots foreground vs background count rates and generates a SkyPlot for a specified time window.

    :param start_time_str: Window start timestamp (ISO format)
    :param end_time_str: Window end timestamp (ISO format)
    :param start_month: Dataset partition start month ('MM-YYYY')
    :param end_month: Dataset partition end month ('MM-YYYY')
    :param output_dir: Destination folder for output figures
    """
    plots_path = output_dir or (DATA_DIR / "plots" / "events")
    plots_path.mkdir(parents=True, exist_ok=True)

    frg_path = DATA_DIR / FOLD_PRED / f"frg_{start_month}_{end_month}.csv"
    bkg_path = DATA_DIR / FOLD_PRED / f"bkg_{start_month}_{end_month}.csv"

    if not frg_path.exists() or not bkg_path.exists():
        logging.error(f"Required matrices not found in {DATA_DIR / FOLD_PRED}")
        return

    logging.info(f"Loading observation matrices: {frg_path.name}")
    frg = pd.read_csv(frg_path)
    bkg = pd.read_csv(bkg_path)

    start_time = pd.to_datetime(start_time_str)
    end_time = pd.to_datetime(end_time_str)
    frg_ts = pd.to_datetime(frg["timestamp"])

    mask = (frg_ts >= start_time) & (frg_ts <= end_time)
    frg_e = frg.loc[mask].copy()
    bkg_e = bkg.loc[mask].copy()

    if frg_e.empty:
        logging.warning("No telemetry samples found within requested time interval.")
        return

    target_channels = ["n0_r0", "n6_r0", "n8_r0", "n0_r1", "n6_r1", "n8_r1", "n0_r2", "n6_r2", "n8_r2"]

    for col in target_channels:
        if col not in frg_e.columns or col not in bkg_e.columns:
            continue

        fig, axs = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
        fig.subplots_adjust(hspace=0)
        fig.suptitle(f"{col} - {start_time_str}")

        # Count rate comparison
        axs[0].plot(frg_e["met"], frg_e[col], "k-.", label="Foreground")
        axs[0].plot(bkg_e["met"], bkg_e[col], "r-", label="NN Background")
        axs[0].set_title("Foreground vs Background")
        axs[0].set_ylabel("Count Rate")
        axs[0].legend(loc="upper right")
        axs[0].grid(True, linestyle="--", alpha=0.5)

        # Residuals
        residual = frg_e[col] - bkg_e[col]
        axs[1].plot(bkg_e["met"], residual, "k-.", label="Residual")
        axs[1].axhline(0, color="gray", linestyle="-", linewidth=0.8)
        axs[1].set_xlabel("Time [MET]")
        axs[1].set_ylabel("Residuals")
        axs[1].grid(True, linestyle="--", alpha=0.5)

        fig_file = plots_path / f"event_{col}_{start_time.strftime('%Y%m%d_%H%M%S')}.png"
        fig.savefig(fig_file, dpi=150, bbox_inches="tight")
        plt.close(fig)

    # SkyPlot orientation at peak window time
    met_event = int(round(float(bkg_e["met"].mean())))
    tmp_dir = DATA_DIR / "tmp_pos"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        cont_finder = ContinuousFtp(met=met_event)
        cont_finder.get_poshist(str(tmp_dir))
        pos_files = list(tmp_dir.glob("*.fits")) + list(tmp_dir.glob("*.fit"))
        if pos_files:
            poshist = PosHist.open(str(pos_files[0]))
            skyplot = SkyPlot()
            skyplot.add_poshist(poshist, trigtime=met_event)
            skyplot_file = plots_path / f"skyplot_{met_event}.png"
            plt.savefig(skyplot_file, dpi=150, bbox_inches="tight")
            plt.close("all")
            logging.info(f"SkyPlot generated: {skyplot_file}")
            pos_files[0].unlink(missing_ok=True)
    except Exception as e:
        logging.warning(f"Could not generate SkyPlot for MET {met_event}: {e}")


if __name__ == "__main__":
    inspect_event_window()