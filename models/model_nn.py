"""
Dynamic neural network background estimation model.
Maps Fermi orbital telemetry and geomagnetic coordinates to continuous expected background count rates.
"""

import datetime
import gc
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as md
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.time import Time
from sklearn.metrics import mean_absolute_error as MAE, median_absolute_error as MeAE
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import BatchNormalization, Dense, Dropout
from tensorflow.keras.models import load_model

import connections.utils.config as cfg
from connections.utils.config import BASE_DIR, GBM_TRIG_DB
from models.utils.losses import loss_max, loss_median
from utils.keys import get_keys

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class ModelNN:
    """Multi-layer Dense Neural Network regressor for 36-channel dynamic background estimation."""

    def __init__(self, start_month: str, end_month: str) -> None:
        self.start_month = start_month
        self.end_month = end_month
        self.list_csv: Optional[List[str]] = None

        self.df_data: Optional[pd.DataFrame] = None
        self.index_date: Optional[pd.Series] = None
        self.scaler: Optional[StandardScaler] = None
        self.nn_r: Optional[tf.keras.Model] = None

        self.col_met: List[str] = ["met"]
        self.col_range: List[str] = get_keys()

        self.col_sat_pos: List[str] = [
            "pos_x", "pos_y", "pos_z", "a", "b", "c", "d", "lat", "lon", "alt",
            "vx", "vy", "vz", "w1", "w2", "w3", "sun_vis", "sun_ra", "sun_dec",
            "earth_r", "earth_ra", "earth_dec", "saa", "l"
        ]

        self.col_det_pos: List[str] = []
        for det in ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]:
            self.col_det_pos.extend([f"{det}_ra", f"{det}_dec", f"{det}_vis"])

        self.col_selected: List[str] = self.col_sat_pos + self.col_det_pos

    def prepare(self, bool_del_trig: bool = True) -> None:
        """Loads daily background features, masks SAA passages, and filters cataloged triggers."""
        logging.info("Preparing feature dataset for neural network training/inference...")

        bkg_dir = cfg.DATA_DIR / cfg.FOLD_BKG

        if self.list_csv and len(self.list_csv) > 0:
            csv_files = [os.path.basename(f) for f in self.list_csv]
        else:
            # Parse date range filters (YYMM format)
            dt_start = datetime.datetime.strptime(self.start_month, "%m-%Y")
            dt_end = datetime.datetime.strptime(self.end_month, "%m-%Y")
            prefix_start = dt_start.strftime("%y%m01.csv")
            # Include all days of end_month up to index 31
            prefix_end = dt_end.strftime("%y%m31.csv")

            csv_files = sorted([
                f for f in os.listdir(str(bkg_dir))
                if f.endswith(".csv") and prefix_start <= f <= prefix_end
            ])

        df_list = []
        for f in csv_files:
            file_path = bkg_dir / f if not os.path.isabs(f) else Path(f)
            try:
                sub_df = pd.read_csv(file_path)
                df_list.append(sub_df)
            except Exception as e:
                logging.warning(f"Could not load daily file {f}: {e}")

        if not df_list:
            raise FileNotFoundError(
                f"No background data files found in {bkg_dir} between {self.start_month} and {self.end_month}"
            )

        df_data = pd.concat(df_list, ignore_index=True)

        # Mask South Atlantic Anomaly passage rows
        logging.info("Masking SAA passage telemetry (saa == 0)...")
        cols_needed = self.col_met + self.col_range + self.col_sat_pos + self.col_det_pos
        df_data = df_data.loc[df_data["saa"] == 0, cols_needed].reset_index(drop=True)

        if bool_del_trig and Path(GBM_TRIG_DB).exists():
            logging.info("Excising known GBM catalog burst intervals from training set...")
            gbm_tri = pd.read_csv(GBM_TRIG_DB)
            valid_mask = np.ones(len(df_data), dtype=bool)

            min_met = df_data["met"].min()
            max_met = df_data["met"].max()
            relevant_trigs = gbm_tri[
                (gbm_tri["met_end_time"] >= min_met) & (gbm_tri["met_time"] <= max_met)
            ]

            met_vals = df_data["met"].values
            for _, r in relevant_trigs.iterrows():
                valid_mask &= (met_vals < r["met_time"]) | (met_vals > r["met_end_time"])

            index_date = pd.Series(valid_mask, index=df_data.index)
        else:
            index_date = pd.Series(True, index=df_data.index)

        # Filter unphysical non-positive count rates
        index_date = index_date & (df_data[self.col_range] > 0).all(axis=1)

        self.df_data = df_data
        self.index_date = index_date
        logging.info(f"Dataset ready. Valid samples: {self.index_date.sum()} / {len(self.df_data)}")

    def train(
        self,
        bool_train: bool = True,
        loss_type: str = "median",
        units: int = 2048,
        epochs: int = 128,
        lr: float = 0.001,
        bs: int = 2048,
        model_pretrain: Optional[str] = None,
        dropout_rate: float = 0.05,
    ) -> None:
        """Trains or loads the background regression neural network."""
        nn_dir = cfg.DATA_DIR / cfg.FOLD_NN
        nn_dir.mkdir(parents=True, exist_ok=True)

        y = self.df_data.loc[self.index_date, self.col_range].astype("float32")
        X = self.df_data.loc[self.index_date, self.col_selected].astype("float32")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, shuffle=True)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        self.scaler = scaler

        if bool_train:
            logging.info("Constructing deep feedforward architecture with BatchNormalization...")
            inputs = tf.keras.Input(shape=(X_train.shape[1],))
            x = Dense(units, activation="relu")(inputs)
            x = BatchNormalization()(x)
            x = Dropout(dropout_rate)(x)

            x = Dense(units, activation="relu")(x)
            x = BatchNormalization()(x)
            x = Dropout(dropout_rate)(x)

            x = Dense(int(units / 2), activation="relu")(x)
            x = BatchNormalization()(x)
            x = Dropout(dropout_rate)(x)

            outputs = Dense(len(self.col_range), activation="relu")(x)
            model = tf.keras.Model(inputs=inputs, outputs=outputs)

            loss_func = loss_median if loss_type == "median" else (loss_max if loss_type == "max" else "mae")
            optimizer = tf.keras.optimizers.Nadam(learning_rate=lr)
            model.compile(loss=loss_func, optimizer=optimizer)

            checkpoint_path = nn_dir / "best_model.keras"
            callbacks = [
                EarlyStopping(monitor="val_loss", patience=20, restore_best_weights=True),
                ModelCheckpoint(str(checkpoint_path), monitor="val_loss", save_best_only=True)
            ]

            logging.info("Training neural model...")
            history = model.fit(
                X_train_scaled, y_train,
                epochs=epochs,
                batch_size=bs,
                validation_split=0.2,
                callbacks=callbacks,
                verbose=1
            )

            self.nn_r = model
            model_name = f"model_{self.start_month}_{self.end_month}"
            model.save(str(nn_dir / f"{model_name}.keras"))
            logging.info(f"Model successfully saved to: {nn_dir / f'{model_name}.keras'}")
        else:
            model_file = nn_dir / (model_pretrain or f"model_{self.start_month}_{self.end_month}.keras")
            logging.info(f"Loading cached model weights from {model_file}...")
            self.nn_r = load_model(
                str(model_file),
                custom_objects={"loss_median": loss_median, "loss_max": loss_max},
                compile=False
            )

    def predict(self, time_to_del: int = 150) -> None:
        """Executes full-timeline background inference and saves foreground/background tables."""
        logging.info("Executing neural background inference across continuous timeline...")
        pred_dir = cfg.DATA_DIR / cfg.FOLD_PRED
        pred_dir.mkdir(parents=True, exist_ok=True)

        X_all = self.scaler.transform(self.df_data[self.col_selected].astype("float32"))
        y_pred_arr = self.nn_r.predict(X_all, batch_size=4096)

        # Standard Fermi mission elapsed time conversion (GPS/MET baseline)
        ts = Time(self.df_data["met"].values, format="fermi").datetime

        df_ori = self.df_data[self.col_range].copy()
        df_ori["met"] = self.df_data["met"].values
        df_ori["timestamp"] = ts

        y_pred = pd.DataFrame(y_pred_arr, columns=self.col_range)
        y_pred["met"] = self.df_data["met"].values
        y_pred["timestamp"] = ts

        if time_to_del > 0:
            logging.info(f"Excising SAA transition boundaries (+/- {time_to_del * 4.096:.1f} s)...")
            gaps = np.where(np.diff(df_ori["met"].values) > 500)[0]
            del_indices = set()
            for idx in gaps:
                low = max(0, idx - time_to_del)
                high = min(len(df_ori), idx + time_to_del)
                del_indices.update(range(low, high))

            df_ori.loc[list(del_indices), self.col_range] = np.nan
            y_pred.loc[list(del_indices), self.col_range] = np.nan

        # Save partitioned matrices
        frg_path = pred_dir / f"frg_{self.start_month}_{self.end_month}.csv"
        bkg_path = pred_dir / f"bkg_{self.start_month}_{self.end_month}.csv"

        df_ori.to_csv(frg_path, index=False)
        y_pred.to_csv(bkg_path, index=False)
        logging.info(f"Foreground matrix saved to: {frg_path}")
        logging.info(f"Background prediction matrix saved to: {bkg_path}")