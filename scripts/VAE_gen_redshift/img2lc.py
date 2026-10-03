"""
Synthesizes 1D lightcurves from 2D spectrographic images.
Integrates vertical energy channels and performs min-max amplitude normalization.
"""

import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from PIL import Image

from connections.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def convert_images_to_lightcurves(
    image_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> None:
    """Reads synthetic/generated GRB spectrogram images and reconstructs lightcurves."""
    source_dir = image_dir or (DATA_DIR / "sample_GRB_images")
    plots_dir = output_dir or (DATA_DIR / "plots" / "vae_redshift")
    plots_dir.mkdir(parents=True, exist_ok=True)

    available_images = sorted(list(source_dir.glob("*.jpg")) + list(source_dir.glob("*.JPG")) + list(source_dir.glob("*.png")))
    if not available_images:
        logging.warning(f"No spectrogram images found in {source_dir}")
        return

    images_to_process = available_images[:3]
    with sns.plotting_context("talk"):
        fig, axes = plt.subplots(len(images_to_process), 1, figsize=(14, 4 * len(images_to_process)), sharex=False)
        if len(images_to_process) == 1:
            axes = [axes]

        for idx, img_path in enumerate(images_to_process):
            img = Image.open(str(img_path)).convert("RGB").resize((516, 128))
            data_arr = np.asarray(img)[:, 2:514, :]  # Shape: (128, 512, 3)

            # Sum across RGB channels then integrate across energy axis
            mono_spectrogram = data_arr.sum(axis=2)
            lightcurve = mono_spectrogram.sum(axis=0)

            # Min-Max normalization
            ptp = np.ptp(lightcurve)
            norm_lc = (lightcurve - lightcurve.min()) / (ptp if ptp != 0 else 1.0)

            axes[idx].step(range(len(norm_lc)), norm_lc, color="black", where="mid")
            axes[idx].set_title(f"Reconstructed Lightcurve: {img_path.name}")
            axes[idx].set_ylabel("Normalized Rate")
            axes[idx].grid(True, linestyle="--", alpha=0.5)

        axes[-1].set_xlabel("Time Bin")
        fig.tight_layout()

        out_file = plots_dir / "reconstructed_lightcurves.png"
        fig.savefig(out_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logging.info(f"Reconstructed lightcurves saved to: {out_file}")


if __name__ == "__main__":
    convert_images_to_lightcurves()