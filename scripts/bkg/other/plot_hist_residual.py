"""
Residual histogram and monthly baseline drift diagnostics.
Plots observed foreground vs neural background distributions across energy channels.
"""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # Headless mode for cluster execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_PRED

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def plot_residual_diagnostics(
    start_month: str = "03-2019",
    end_month: str = "07-2019",
    col_hist: str = "n9_r2",
    output_dir: Optional[Path] = None
) -> None:
    """
    Plots residual distributions and monthly delta trends between foreground and background.

    :param start_month: Start month format 'MM-YYYY'
    :param end_month: End month format 'MM-YYYY'
    :param col_hist: Channel to inspect for histograms
    :param output_dir: Destination folder for output figures
    """
    plots_path = output_dir or (DATA_DIR / "plots" / "residuals")
    plots_path.mkdir(parents=True, exist_ok=True)

    pred_dir = DATA_DIR / FOLD_PRED
    frg_file = pred_dir / f"frg_{start_month}_{end_month}.csv"
    bkg_file = pred_dir / f"bkg_{start_month}_{end_month}.csv"

    if not frg_file.exists() or not bkg_file.exists():
        logging.error(f"Foreground or background files missing in {pred_dir}")
        return

    logging.info(f"Loading matrices for {start_month} to {end_month}...")
    df_ori = pd.read_csv(frg_file)
    y_pred = pd.read_csv(bkg_file)

    # Ensure datetime format for month indexing
    df_ori["timestamp"] = pd.to_datetime(df_ori["timestamp"], errors="coerce")
    months = sorted(df_ori["timestamp"].dt.month.dropna().unique().astype(int))

    # 1. Plot histograms per month
    for m in months:
        mask_month = df_ori["timestamp"].dt.month == m
        sub_frg = df_ori.loc[mask_month, col_hist].dropna()
        sub_bkg = y_pred.loc[mask_month, col_hist].dropna()

        if sub_frg.empty or sub_bkg.empty:
            continue

        # Filter quantile outliers
        q_low, q_high = sub_frg.quantile(0.001), sub_frg.quantile(0.99)
        frg_filt = sub_frg[(sub_frg >= q_low) & (sub_frg <= q_high)]
        bkg_filt = sub_bkg[(sub_bkg >= q_low) & (sub_bkg <= q_high)]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(frg_filt, bins=40, alpha=0.5, label="Observed Foreground", color="black")
        ax.hist(bkg_filt, bins=40, alpha=0.5, label="NN Background", color="red")

        diff_med = frg_filt.median() - bkg_filt.median()
        ax.set_title(f"Month {m:02d} ({col_hist}) - Median Diff: {diff_med:.2f}")
        ax.set_xlabel("Count Rate")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)

        fig.savefig(plots_path / f"hist_res_{col_hist}_month_{m:02d}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    # 2. Monthly Median Drift Analysis across channels
    logging.info("Computing monthly median delta across all detector channels...")
    diff_records = []
    energy_cols = [c for c in y_pred.columns if "_r" in c]

    for m in months:
        mask_m = df_ori["timestamp"].dt.month == m
        med_frg = df_ori.loc[mask_m, energy_cols].median()
        med_bkg = y_pred.loc[mask_m, energy_cols].median()
        diff_row = med_frg - med_bkg
        diff_row["month"] = m
        diff_records.append(diff_row)

    if diff_records:
        df_diff = pd.DataFrame(diff_records).set_index("month")

        fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
        for r_idx in range(3):
            r_cols = [c for c in energy_cols if f"_r{r_idx}" in c]
            df_diff[r_cols].plot(ax=axes[r_idx], marker="o")
            axes[r_idx].set_ylabel(f"Range {r_idx} (Frg - Bkg)")
            axes[r_idx].grid(True, linestyle="--", alpha=0.5)
            if r_idx == 0:
                axes[r_idx].set_title("Monthly Median Count Rate Residuals (Original - Predicted)")

        axes[-1].set_xlabel("Month")
        axes[1].legend(loc="center left", bbox_to_anchor=(1.01, 0.5), ncol=2, fontsize=8)

        drift_plot_file = plots_path / "monthly_residual_drift.png"
        fig.savefig(drift_plot_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logging.info(f"Diagnostic drift plot saved to: {drift_plot_file}")


if __name__ == "__main__":
    plot_residual_diagnostics()