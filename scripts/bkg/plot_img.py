"""
Batch figure production script for publications and diagnostics.
Generates orbit-downsampled comparisons, residual trends, and GRB lightcurves.
"""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from connections.utils.config import DATA_DIR, FOLD_PRED

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def generate_publication_plots(output_dir: Optional[Path] = None) -> None:
    """Generates benchmark plots matching the DeepGRB paper figures."""
    save_path = output_dir or (DATA_DIR / "plots" / "paper_figures")
    save_path.mkdir(parents=True, exist_ok=True)
    pred_path = DATA_DIR / FOLD_PRED

    # 1. Figure: Daily Residual Profile (2019-05-21)
    file_frg_19 = pred_path / "frg_01-2019_07-2019_MAE.csv"
    file_bkg_19 = pred_path / "bkg_01-2019_07-2019_MAE.csv"

    # Fallback to standard names if MAE suffix is absent
    if not file_frg_19.exists():
        file_frg_19 = pred_path / "frg_03-2019_07-2019.csv"
        file_bkg_19 = pred_path / "bkg_03-2019_07-2019.csv"

    if file_frg_19.exists() and file_bkg_19.exists():
        logging.info("Generating Figure 1: Daily residual profile...")
        df_ori = pd.read_csv(file_frg_19)
        y_pred = pd.read_csv(file_bkg_19)
        df_ori["dt"] = pd.to_datetime(df_ori["timestamp"])

        mask = (df_ori["dt"] >= "2019-05-21 00:00:00") & (df_ori["dt"] < "2019-05-22 00:00:00")
        sub_frg = df_ori.loc[mask]
        sub_bkg = y_pred.loc[mask]

        if not sub_frg.empty:
            det_rng = "n4_r1"
            with sns.plotting_context("talk"):
                fig, axs = plt.subplots(2, 1, sharex=True, figsize=(18, 9))
                fig.subplots_adjust(hspace=0)
                fig.suptitle(f"{det_rng} - 2019-05-21")

                axs[0].plot(sub_frg["dt"], sub_frg[det_rng], "k-.", label="Observed")
                axs[0].plot(sub_frg["dt"], sub_bkg[det_rng], "r-", label="Predicted Bkg")
                axs[0].set_ylabel("Count Rate")
                axs[0].legend(loc="upper right")
                axs[0].grid(True, linestyle="--", alpha=0.5)

                axs[1].plot(sub_frg["dt"], sub_frg[det_rng] - sub_bkg[det_rng], "k-.")
                axs[1].axhline(0, color="gray", linestyle="-", linewidth=0.8)
                axs[1].set_xlabel("Time (UTC)")
                axs[1].set_ylabel("Residuals")
                axs[1].grid(True, linestyle="--", alpha=0.5)

                fig.savefig(save_path / "n4_r1_2019_05_21.png", dpi=150, bbox_inches="tight")
                plt.close(fig)

            # Scatter y_pred vs y_true
            with sns.plotting_context("talk"):
                fig, ax = plt.subplots(figsize=(10, 8))
                for ch in ["n4_r0", "n4_r1", "n4_r2"]:
                    ax.scatter(sub_frg[ch], sub_bkg[ch], s=10, alpha=0.3, label=ch)
                ax.plot([0, 600], [0, 600], "k--", label="Ideal 1:1")
                ax.set_xlim([0, 600])
                ax.set_ylim([0, 600])
                ax.set_xlabel("Observed Signal")
                ax.set_ylabel("Predicted Background")
                ax.legend()
                ax.grid(True, linestyle="--", alpha=0.5)
                fig.savefig(save_path / "bkg_est.png", dpi=150, bbox_inches="tight")
                plt.close(fig)

    # 2. Figure: Orbit-Averaged Downsampled Lightcurves (Solar Minimum / Maximum)
    for epoch_label, start_m, end_m in [("solarmin_2020", "01-2020", "01-2021"), ("solarmax_2014", "01-2014", "01-2015")]:
        f_frg = pred_path / f"frg_{start_m}_{end_m}.csv"
        f_bkg = pred_path / f"bkg_{start_m}_{end_m}.csv"

        if not f_frg.exists() or not f_bkg.exists():
            continue

        logging.info(f"Generating orbit-averaged plots for {epoch_label}...")
        df_f = pd.read_csv(f_frg)
        df_b = pd.read_csv(f_bkg)

        for orbit_bin in [1, 16]:
            orbit_seconds = 96.0 * orbit_bin * 60.0
            group_key = df_f["met"] // orbit_seconds

            df_f_down = df_f.groupby(group_key).mean(numeric_only=True)
            df_b_down = df_b.groupby(group_key).mean(numeric_only=True)
            ts_down = df_f["timestamp"].groupby(group_key).first()

            det_target = "n5_r0"
            if det_target not in df_f_down.columns:
                continue

            with sns.plotting_context("talk"):
                fig, axs = plt.subplots(2, 1, sharex=True, figsize=(18, 9))
                fig.subplots_adjust(hspace=0)
                fig.suptitle(f"{det_target} - {epoch_label} (Orbit bin: {orbit_bin})")

                x_axis = pd.to_datetime(ts_down)
                axs[0].plot(x_axis, df_f_down[det_target], "k-.", label="Observed (Averaged)")
                axs[0].plot(x_axis, df_b_down[det_target], "r-", label="Predicted (Averaged)")
                axs[0].set_ylabel("Count Rate")
                axs[0].legend(loc="upper right")
                axs[0].grid(True, linestyle="--", alpha=0.5)

                axs[1].plot(x_axis, df_f_down[det_target] - df_b_down[det_target], "k-.")
                axs[1].axhline(0, color="gray", linestyle="-", linewidth=0.8)
                axs[1].set_xlabel("Date")
                axs[1].set_ylabel("Residuals")
                axs[1].grid(True, linestyle="--", alpha=0.5)

                fig.savefig(save_path / f"{det_target}_{epoch_label}_orbit_{orbit_bin}.png", dpi=150, bbox_inches="tight")
                plt.close(fig)

    logging.info(f"All available figures successfully exported to: {save_path}")


if __name__ == "__main__":
    generate_publication_plots()