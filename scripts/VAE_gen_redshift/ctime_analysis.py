"""
Continuous CTIME spectral and lightcurve analyzer.
Extracts energy-channel count rates, rebins time series, and plots spectro-temporal heatmaps.
"""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Headless cluster mode
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
import pandas as pd
import seaborn as sns

from gbm.binning.binned import rebin_by_time
from gbm.data import Ctime

from connections.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def analyze_ctime_file(ctime_path: Optional[Path] = None, output_dir: Optional[Path] = None) -> None:
    """Analyzes a daily CTIME FITS file and exports diagnostic lightcurves and heatmaps."""
    ctime_dir = DATA_DIR / "ctime"
    plots_dir = output_dir or (DATA_DIR / "plots" / "vae_redshift")
    plots_dir.mkdir(parents=True, exist_ok=True)

    if ctime_path is None:
        available = list(ctime_dir.glob("*.pha")) + list(ctime_dir.glob("*.fits"))
        if not available:
            logging.warning(f"No CTIME files found in {ctime_dir}")
            return
        target_file = available[0]
    else:
        target_file = ctime_path

    logging.info(f"Opening CTIME observation: {target_file.name}")
    c_data = Ctime.open(str(target_file))

    # Rebin and extract energy-integrated lightcurve
    rebinned_cspec = c_data.rebin_time(rebin_by_time, 0.256)
    lightcurve = rebinned_cspec.to_lightcurve(energy_range=(30.0, 500.0))

    centroids = lightcurve.centroids
    mask = (centroids > -20.0) & (centroids < 20.0)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(centroids[mask], lightcurve.rates[mask], "-x", color="black", label="30-500 keV")
    ax.set_title(f"Rebinned Lightcurve (0.256s) - {target_file.stem}")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Count Rate [counts/s]")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.savefig(plots_dir / f"ctime_lc_{target_file.stem}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 2D Spectro-temporal Heatmap
    time_mask = (c_data.data.time_centroids >= 0.0) & (c_data.data.time_centroids < 15.0)
    counts_subset = c_data.data.counts[time_mask].T

    pd_ctime = pd.DataFrame(
        counts_subset,
        index=np.around(c_data.data.energy_centroids, 1),
        columns=np.around(c_data.data.time_centroids[time_mask], 2)
    )

    fig_heat, ax_heat = plt.subplots(figsize=(16, 8))
    sns.heatmap(pd_ctime, annot=False, fmt="d", cmap="viridis", linewidths=0.2, ax=ax_heat, norm=Normalize())
    ax_heat.set_title(f"Energy vs Time Spectrogram - {target_file.stem}")
    ax_heat.set_xlabel("Time [s]")
    ax_heat.set_ylabel("Energy Channel Centroid [keV]")

    heatmap_file = plots_dir / f"ctime_heatmap_{target_file.stem}.png"
    fig_heat.savefig(heatmap_file, dpi=150, bbox_inches="tight")
    plt.close(fig_heat)
    logging.info(f"Heatmap successfully saved to: {heatmap_file}")


if __name__ == "__main__":
    analyze_ctime_file()