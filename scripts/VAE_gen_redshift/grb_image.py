"""
Convolutional Autoencoder preprocessing and training module for 2D spectro-temporal GRB images.
Encodes Time-Tagged Event (TTE) count spectrograms into a compact latent representation.
"""

import logging
from pathlib import Path
import pickle
from typing import List, Tuple
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers

from gbm.binning.unbinned import bin_by_time
from gbm.data import TTE
from gbm.finder import BurstCatalog
from connections.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

MAX_TIME_BINS = 4096  # Adjusted to power of 2 for symmetric downsampling/upsampling
ENERGY_CHANNELS = 128


def extract_tte_matrices(tte_dir: Path, output_pkl: Path) -> np.ndarray:
    """Bins TTE files into uniform 2D (time x energy) matrices and saves pickle array."""
    tte_files = sorted(list(tte_dir.glob("*.fit*")) + list(tte_dir.glob("*.pha*")))
    if not tte_files:
        raise FileNotFoundError(f"No TTE files found in {tte_dir}")

    logging.info(f"Parsing {len(tte_files)} TTE events into uniform spectrograms...")
    dataset = []

    for f in tte_files:
        try:
            tte_obj = TTE.open(str(f))
            phaii = tte_obj.to_phaii(bin_by_time, 0.256, time_ref=0.0)
            counts = phaii.data.counts  # Shape: (T, 128)

            # Pad or truncate to MAX_TIME_BINS
            if counts.shape[0] < MAX_TIME_BINS:
                diff = MAX_TIME_BINS - counts.shape[0]
                padded = np.pad(counts, [(0, diff), (0, 0)], mode="constant", constant_values=0)
            else:
                padded = counts[:MAX_TIME_BINS, :]

            dataset.append(padded)
        except Exception as e:
            logging.warning(f"Could not parse {f.name}: {e}")

    ds_array = np.array(dataset, dtype="float32")
    with open(output_pkl, "wb") as f_out:
        pickle.dump(ds_array, f_out)

    logging.info(f"Saved dataset of shape {ds_array.shape} to {output_pkl}")
    return ds_array


def build_conv_autoencoder(input_shape: Tuple[int, int, int] = (MAX_TIME_BINS, ENERGY_CHANNELS, 1)) -> tf.keras.Model:
    """Builds a symmetric 2D Convolutional Autoencoder."""
    inputs = tf.keras.Input(shape=input_shape)

    # Encoder
    x = layers.Conv2D(16, (3, 3), activation="relu", padding="same")(inputs)
    x = layers.MaxPooling2D((2, 2), padding="same")(x)
    x = layers.Conv2D(8, (3, 3), activation="relu", padding="same")(x)
    x = layers.MaxPooling2D((2, 2), padding="same")(x)
    x = layers.Conv2D(8, (3, 3), activation="relu", padding="same")(x)
    encoded = layers.MaxPooling2D((2, 2), padding="same")(x)

    # Decoder
    x = layers.Conv2D(8, (3, 3), activation="relu", padding="same")(encoded)
    x = layers.UpSampling2D((2, 2))(x)
    x = layers.Conv2D(8, (3, 3), activation="relu", padding="same")(x)
    x = layers.UpSampling2D((2, 2))(x)
    x = layers.Conv2D(16, (3, 3), activation="relu", padding="same")(x)
    x = layers.UpSampling2D((2, 2))(x)
    decoded = layers.Conv2D(1, (3, 3), activation="sigmoid", padding="same")(x)

    autoencoder = tf.keras.Model(inputs=inputs, outputs=decoded)
    autoencoder.compile(optimizer="adam", loss="mse")
    return autoencoder


def train_autoencoder(epochs: int = 30, batch_size: int = 8) -> tf.keras.Model:
    """Pipeline entrypoint: prepares data and trains the autoencoder."""
    tte_folder = DATA_DIR / "tte"
    dataset_pkl = DATA_DIR / "tte_spectrograms.pkl"

    if dataset_pkl.exists():
        logging.info(f"Loading cached spectrogram dataset from: {dataset_pkl}")
        with open(dataset_pkl, "rb") as f:
            data = pickle.load(f)
    else:
        data = extract_tte_matrices(tte_folder, dataset_pkl)

    # Min-max normalization for sigmoid activation output
    max_val = np.percentile(data, 99.5) or 1.0
    normalized_data = np.clip(data / max_val, 0.0, 1.0)
    normalized_data = np.expand_dims(normalized_data, axis=-1)

    split_idx = int(0.8 * len(normalized_data))
    train_x = normalized_data[:split_idx]
    test_x = normalized_data[split_idx:]

    autoencoder = build_conv_autoencoder()
    logging.info("Training Convolutional Autoencoder...")
    autoencoder.fit(
        train_x, train_x,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(test_x, test_x),
        verbose=1
    )

    save_path = DATA_DIR / "nn_model" / "grb_autoencoder.keras"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    autoencoder.save(str(save_path))
    logging.info(f"Trained autoencoder saved to: {save_path}")
    return autoencoder


if __name__ == "__main__":
    train_autoencoder()