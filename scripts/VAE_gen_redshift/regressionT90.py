"""
Nonlinear regression and t-SNE manifold visualization for GRB durations ($T_{90}$).
Fits Random Forest / XGBoost models using prompt emission spectral properties.
"""

import logging
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.manifold import TSNE
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from connections.utils.config import DATA_DIR
from models.load_data import df_burst_catalog

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def run_t90_regression() -> None:
    """Trains regression models for T90 duration and generates t-SNE manifold projections."""
    plots_dir = DATA_DIR / "plots" / "vae_redshift"
    plots_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Loading cleaned Fermi GBM burst catalog...")
    df_grb = df_burst_catalog(download=False, dropna=True)
    if df_grb.empty or "t90" not in df_grb.columns:
        logging.error("Burst catalog empty or missing 't90' column.")
        return

    # Filter physical positive T90 durations
    df_grb = df_grb[df_grb["t90"] > 0].copy()

    X = df_grb.drop(columns=["t90"]).select_dtypes(include=["number"]).astype("float64")
    y = np.log(df_grb["t90"].values)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

    # Train Random Forest Regressor
    rf = RandomForestRegressor(n_estimators=500, max_depth=15, min_samples_split=4, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    r2_score = rf.score(X_test, y_test)
    logging.info(f"Random Forest Regressor R^2 Score on Test Set: {r2_score:.4f}")

    # Plot actual vs predicted log(T90)
    y_pred = rf.predict(X_test)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(y_test, y_pred, alpha=0.4, color="crimson", edgecolors="none")
    lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
    ax.plot(lims, lims, "k--", alpha=0.75)
    ax.set_xlabel(r"Observed $\ln(T_{90})$")
    ax.set_ylabel(r"Predicted $\ln(T_{90})$")
    ax.set_title(r"GRB Duration Regression: Observed vs Predicted $\ln(T_{90})$")
    ax.grid(True, linestyle="--", alpha=0.5)

    scatter_file = plots_dir / "regression_t90_scatter.png"
    fig.savefig(scatter_file, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # t-SNE Manifold Projection across spectral parameters
    col_selected = [
        "flnc_comp_ergflux", "flux_1024", "flnc_plaw_phtflux", "pflx_band_alpha",
        "pflx_comp_epeak", "pflx_plaw_phtflux", "flnc_sbpl_pivot", "flnc_plaw_pivot", "pflx_comp_pivot"
    ]
    available_cols = [c for c in col_selected if c in df_grb.columns]

    if len(available_cols) >= 3:
        logging.info("Computing t-SNE 2D manifold embedding...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_grb[available_cols])

        for perp in [30, 50]:
            tsne = TSNE(n_components=2, perplexity=perp, random_state=42, n_jobs=-1)
            embedded = tsne.fit_transform(X_scaled)

            fig_tsne, ax_tsne = plt.subplots(figsize=(9, 7))
            sc = ax_tsne.scatter(
                embedded[:, 0], embedded[:, 1],
                c=df_grb["t90"], s=18, alpha=0.8,
                cmap="viridis", norm=matplotlib.colors.LogNorm()
            )
            cbar = plt.colorbar(sc, ax=ax_tsne)
            cbar.set_label(r"$T_{90}$ Duration [s]")
            ax_tsne.set_title(f"t-SNE Spectral Manifold Projection (Perplexity: {perp})")
            ax_tsne.set_xlabel("t-SNE Dimension 1")
            ax_tsne.set_ylabel("t-SNE Dimension 2")
            ax_tsne.grid(True, linestyle="--", alpha=0.3)

            tsne_file = plots_dir / f"tsne_perplexity_{perp}.png"
            fig_tsne.savefig(tsne_file, dpi=150, bbox_inches="tight")
            plt.close(fig_tsne)

        logging.info(f"t-SNE projections saved to: {plots_dir}")


if __name__ == "__main__":
    run_t90_regression()