"""
Neural-network background estimator (Crupi et al. 2023).

Maps Fermi orbital/attitude features to the 36 NaI count-rate channels. The
architecture and training recipe follow the upstream code that produced the
published results. A trained model is stored as a *bundle* folder:

    model.keras | model.h5   the network
    scaler.joblib            the StandardScaler fitted on the training inputs
    metadata.json            period, seed, hyper-parameters, versions, per-channel MAE

Predictions are written to explicit output paths and never overwrite inputs.
"""

import json
import logging
import platform
import random
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
import tensorflow as tf
from astropy.time import Time
from sklearn.metrics import mean_absolute_error as MAE
from sklearn.metrics import median_absolute_error as MeAE
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.callbacks import Callback, EarlyStopping, LearningRateScheduler, ModelCheckpoint
from tensorflow.keras.layers import BatchNormalization, Dense, Dropout
from tensorflow.keras.models import load_model

import connections.utils.config as cfg
from models.utils.losses import loss_max, loss_median
from utils.keys import get_keys
from utils.period import window_days

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

SAA_GAP_SECONDS = 500.0
SPLIT_SEED = 0  # upstream train_test_split(random_state=0): fixes the scaler

COL_SAT_POS = [
    "pos_x", "pos_y", "pos_z", "a", "b", "c", "d", "lat", "lon", "alt",
    "vx", "vy", "vz", "w1", "w2", "w3", "sun_vis", "sun_ra", "sun_dec",
    "earth_r", "earth_ra", "earth_dec", "saa", "l",
]
COL_DET_POS = [f"{det}_{k}" for det in [f"n{i}" for i in "0123456789ab"] for k in ("ra", "dec", "vis")]


def set_seeds(seed: int) -> None:
    """Seeds python, numpy and TensorFlow."""
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)


def met_to_utc(met: Sequence[float]) -> pd.Series:
    """Fermi MET seconds -> UTC timestamps (the 'fermi' time format is on the TT scale)."""
    return pd.Series(Time(np.asarray(met, dtype=float), format="fermi").utc.to_datetime())


def saa_mask_indices(met: Sequence[float], time_to_del: int, gap_seconds: float = SAA_GAP_SECONDS) -> np.ndarray:
    """
    Row positions to blank around every time gap > gap_seconds (SAA passages).

    Upstream rule: for each first row after a gap, rows [ind - time_to_del, ind + time_to_del)
    are removed, i.e. time_to_del bins on each side. Windows are clipped to the table
    (upstream clipped them to the first/last gap, leaving those two sides unmasked).
    """
    met = np.asarray(met, dtype=float)
    after_gap = np.where(np.diff(met) > gap_seconds)[0] + 1
    mask = np.zeros(len(met), dtype=bool)
    for ind in after_gap:
        mask[max(ind - time_to_del, 0):min(ind + time_to_del, len(met))] = True
    return np.where(mask)[0]


# Convergence check (non-blocking): the final val_loss should be well below the MAE of a constant
# per-channel median predictor (benchmark/analysis/lr_check.py: 20.4 on the 2019 validation split).
CONVERGENCE_MAX_RATIO = 0.5


def convergence_check(y_fit: np.ndarray, y_val: np.ndarray, history: Dict[str, list]) -> Dict:
    """Compares the validation loss with trivial predictors (same split); never stops training."""
    y_fit, y_val = np.asarray(y_fit, dtype=float), np.asarray(y_val, dtype=float)
    ref_median = float(np.mean(np.abs(y_val - np.median(y_fit, axis=0))))
    ref_zero = float(np.mean(np.abs(y_val)))
    val = [float(v) for v in history.get("val_loss", [])]
    final, best = (val[-1], min(val)) if val else (float("nan"), float("nan"))
    ratio = final / ref_median if ref_median > 0 else float("nan")
    return {"final_val_loss": final, "best_val_loss": best,
            "ref_constant_median_val_mae": ref_median, "ref_zero_val_mae": ref_zero,
            "final_over_constant_median": ratio, "max_ratio": CONVERGENCE_MAX_RATIO,
            "ok": bool(np.isfinite(ratio) and ratio < CONVERGENCE_MAX_RATIO)}


def report(msg: str = "") -> None:
    """Training report line on stdout, flushed at once (readable under nohup / python -u)."""
    print(msg, flush=True)


class EpochReport(Callback):
    """One stdout line per epoch: loss, val_loss, learning rate, elapsed time. Does not affect training."""

    def __init__(self, epochs: int) -> None:
        super().__init__()
        self.epochs = epochs
        self.t0 = time.time()

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        lr = self.model.optimizer.learning_rate
        lr = float(lr.numpy() if hasattr(lr, "numpy") else lr)
        report(f"[train] epoch {epoch + 1:3d}/{self.epochs}  loss {logs.get('loss', float('nan')):.4f}  "
               f"val_loss {logs.get('val_loss', float('nan')):.4f}  lr {lr:.2e}  elapsed {time.time() - self.t0:7.1f} s")


def _lr_schedule(base_lr: float):
    """Upstream piecewise learning rate: x12.5 for 4 epochs, x2 until epoch 12, then /2."""
    def schedule(epoch, _lr):
        if epoch < 4:
            return base_lr * 12.5
        if epoch < 12:
            return base_lr * 2
        return base_lr / 2
    return schedule


def count_nonpositive_predictions(bkg_path: Path) -> Dict[str, int]:
    """Cells of a background matrix with predicted rate <= 0, and bins where any/all channels are <= 0."""
    keys = get_keys()
    b = pd.read_csv(bkg_path, usecols=keys).to_numpy(dtype=float)
    bad = b <= 0  # NaN (masked) compares False
    return {"cells": int(bad.sum()), "bins_any_channel": int(bad.any(axis=1).sum()),
            "bins_all_channels": int(bad.all(axis=1).sum()), "channels": len(keys), "bins": int(len(b))}


class ModelNN:
    """Dense regressor from orbital features to the 36 NaI count rates."""

    def __init__(self, start_date: str = cfg.START_DATE, end_date: str = cfg.END_DATE,
                 bkg_dir: Optional[Path] = None, trig_catalog_path: Optional[Path] = None) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.bkg_dir = Path(bkg_dir or cfg.DATA_DIR / cfg.FOLD_BKG)
        self.trig_catalog_path = Path(trig_catalog_path or cfg.GBM_TRIG_DB)

        self.col_met: List[str] = ["met"]
        self.col_range: List[str] = get_keys()
        self.col_sat_pos: List[str] = list(COL_SAT_POS)
        self.col_det_pos: List[str] = list(COL_DET_POS)
        self.col_selected: List[str] = self.col_sat_pos + self.col_det_pos

        self.df_data: Optional[pd.DataFrame] = None
        self.index_date: Optional[pd.Series] = None
        self.scaler: Optional[StandardScaler] = None
        self.nn_r: Optional[tf.keras.Model] = None
        self.metadata: Dict = {}

    # ------------------------------------------------------------------ data
    def prepare(self, bool_del_trig: bool = True) -> None:
        """Loads the daily tables of the window, drops SAA rows, flags rows usable for training."""
        days = window_days(self.start_date, self.end_date)
        files = [self.bkg_dir / f"{d}.csv" for d in days if (self.bkg_dir / f"{d}.csv").exists()]
        missing = len(days) - len(files)
        logging.info(f"Loading {len(files)}/{len(days)} daily tables {self.start_date} -> {self.end_date}"
                     + (f" ({missing} missing)" if missing else ""))
        if not files:
            raise FileNotFoundError(f"No daily tables in {self.bkg_dir} for {self.start_date} -> {self.end_date}")

        df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
        cols = self.col_met + self.col_range + self.col_sat_pos + self.col_det_pos
        df = df.loc[df["saa"] == 0, cols].reset_index(drop=True)

        index_date = pd.Series(True, index=df.index)
        if bool_del_trig:
            # Training excludes the intervals of cataloged triggers (upstream: keep met <= start or met >= end)
            trig = pd.read_csv(self.trig_catalog_path)
            met = df["met"].to_numpy()
            keep = np.ones(len(df), dtype=bool)
            trig = trig[(trig["met_end_time"] >= met.min()) & (trig["met_time"] <= met.max())]
            for t0, t1 in zip(trig["met_time"].to_numpy(), trig["met_end_time"].to_numpy()):
                keep &= (met <= t0) | (met >= t1)
            index_date &= keep
        index_date &= (df[self.col_range] > 0).all(axis=1)

        self.df_data = df
        self.index_date = index_date
        logging.info(f"Dataset ready: {len(df)} rows outside SAA, {int(index_date.sum())} usable for training")

    def _split(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        y = self.df_data.loc[self.index_date, self.col_range].astype("float32")
        X = self.df_data.loc[self.index_date, self.col_selected].astype("float32")
        return train_test_split(X, y, test_size=0.25, random_state=SPLIT_SEED, shuffle=True)

    def fit_scaler(self) -> StandardScaler:
        """StandardScaler on the training split (deterministic: same data -> same scaler)."""
        X_train, _, _, _ = self._split()
        self.scaler = StandardScaler().fit(X_train)
        return self.scaler

    # --------------------------------------------------------------- training
    def train(self, bundle_dir: Path, seed: int = 0, loss_type: str = "mean", units: int = 2048,
              epochs: int = 64, lr: float = 0.0008, bs: int = 2048, dropout_rate: float = 0.02,
              extra_metadata: Optional[Dict] = None) -> Dict:
        """
        Trains with the upstream recipe and saves a bundle. Returns the metadata.
        A readable report (parameters, rows, one line per epoch, per-channel MAE, duration)
        is printed on stdout; extra_metadata (e.g. git commit, run label) is stored in metadata.json.
        """
        t_start = time.time()
        bundle_dir = Path(bundle_dir)
        if bundle_dir.exists():
            raise FileExistsError(f"Refusing to overwrite model bundle {bundle_dir}")
        set_seeds(seed)
        X_train, X_test, y_train, y_test = self._split()
        self.scaler = StandardScaler().fit(X_train)
        X_train_s, X_test_s = self.scaler.transform(X_train), self.scaler.transform(X_test)

        # Keras validation_split takes the last 30% of the training arrays, without shuffling
        n_fit = int(len(X_train) * (1 - 0.3))
        report("=" * 70)
        report(f"[train] bundle      : {bundle_dir}")
        report(f"[train] period      : {self.start_date} -> {self.end_date}")
        report(f"[train] seed        : {seed}  (split seed {SPLIT_SEED})")
        report(f"[train] parameters  : loss={loss_type} units={units} epochs={epochs} lr={lr} batch={bs} "
               f"dropout={dropout_rate} validation_split=0.3 early_stopping(min_delta=0.01, patience=32)")
        report(f"[train] rows        : pool {len(X_train) + len(X_test)} = fit {n_fit} + validation "
               f"{len(X_train) - n_fit} + test {len(X_test)}  (features {X_train.shape[1]}, targets {y_train.shape[1]})")
        report(f"[train] devices     : {[d.name for d in tf.config.list_physical_devices('GPU')] or 'CPU only'}")
        report("=" * 70)

        inputs = tf.keras.Input(shape=(X_train.shape[1],))
        x = inputs
        for n_units in (units, units, int(units / 2)):
            x = Dense(n_units, activation="relu")(x)
            x = BatchNormalization()(x)
            x = Dropout(dropout_rate)(x)
        outputs = Dense(len(self.col_range), activation="relu")(x)
        model = tf.keras.Model(inputs=inputs, outputs=outputs)

        loss = {"max": loss_max, "median": loss_median}.get(loss_type, "mae")
        model.compile(loss=loss, optimizer=tf.keras.optimizers.Nadam(learning_rate=lr, beta_1=0.9, beta_2=0.99, epsilon=1e-07))

        bundle_dir.mkdir(parents=True, exist_ok=False)
        checkpoint = bundle_dir / "best_checkpoint.keras"
        t_fit = time.time()
        history = model.fit(
            X_train_s, y_train, epochs=epochs, batch_size=bs, validation_split=0.3, verbose=0,
            callbacks=[
                EarlyStopping(monitor="val_loss", mode="min", min_delta=0.01, patience=32),
                ModelCheckpoint(str(checkpoint), monitor="val_loss", mode="min", save_best_only=True),
                LearningRateScheduler(_lr_schedule(lr)),
                EpochReport(epochs),
            ],
        )
        fit_seconds = time.time() - t_fit
        self.nn_r = load_model(str(checkpoint), compile=False, custom_objects={"loss_median": loss_median, "loss_max": loss_max})

        metrics = self._channel_metrics(X_train_s, y_train, X_test_s, y_test)
        conv = convergence_check(y_train.iloc[:n_fit].to_numpy(), y_train.iloc[n_fit:].to_numpy(), history.history)
        val_loss = history.history.get("val_loss", [])
        best_epoch = int(np.argmin(val_loss)) + 1 if val_loss else None
        report("-" * 70)
        report(f"[train] epochs run {len(history.history.get('loss', []))}/{epochs}; best val_loss "
               f"{min(val_loss):.4f} at epoch {best_epoch}" if val_loss else "[train] no validation loss recorded")
        report("[train] per-channel MAE (best checkpoint)       train      test   MeAE test")
        for ch, m in metrics.items():
            report(f"[train]   {ch:<38s} {m['mae_train']:9.3f} {m['mae_test']:9.3f} {m['meae_test']:9.3f}")
        report(f"[train]   {'mean over channels':<38s} {np.mean([m['mae_train'] for m in metrics.values()]):9.3f} "
               f"{np.mean([m['mae_test'] for m in metrics.values()]):9.3f}")

        self.metadata = {
            "source": "trained",
            "seed": seed,
            "hyperparameters": {"loss_type": loss_type, "units": units, "epochs": epochs, "lr": lr,
                                "batch_size": bs, "dropout": dropout_rate, "validation_split": 0.3,
                                "early_stopping": {"min_delta": 0.01, "patience": 32}, "split_seed": SPLIT_SEED},
            "rows": {"fit": n_fit, "validation": len(X_train) - n_fit, "test": len(X_test)},
            "epochs_run": len(history.history.get("loss", [])),
            "best_epoch": best_epoch,
            "history": {k: [float(v) for v in vals] for k, vals in history.history.items() if k in ("loss", "val_loss")},
            "metrics": metrics,
            "convergence": conv,
            "devices": [d.name for d in tf.config.list_physical_devices("GPU")] or ["CPU"],
            "training_seconds": round(fit_seconds, 1),
            "total_seconds": round(time.time() - t_start, 1),
        }
        self.metadata.update(dict(extra_metadata or {}))
        self.save_bundle(bundle_dir, model_file="model.keras")
        checkpoint.unlink(missing_ok=True)
        report(f"[train] convergence: final val_loss {conv['final_val_loss']:.3f} (best {conv['best_val_loss']:.3f}); "
               f"constant per-channel median {conv['ref_constant_median_val_mae']:.3f}, always zero {conv['ref_zero_val_mae']:.3f}; "
               f"ratio {conv['final_over_constant_median']:.2f} -> "
               + ("OK" if conv["ok"] else f"WARNING: final val_loss not well below the constant predictor (ratio >= {CONVERGENCE_MAX_RATIO})"))
        if not conv["ok"]:
            logging.warning("Training convergence check failed (non-blocking): see metadata.json 'convergence'.")
        report(f"[train] fit time {fit_seconds / 60:.1f} min; total (incl. metrics and saving) "
               f"{(time.time() - t_start) / 60:.1f} min; bundle {bundle_dir}")
        report("=" * 70)
        return self.metadata

    def _channel_metrics(self, X_train_s, y_train, X_test_s, y_test) -> Dict[str, Dict[str, float]]:
        pred_train = self.nn_r.predict(X_train_s, batch_size=8192, verbose=0)
        pred_test = self.nn_r.predict(X_test_s, batch_size=8192, verbose=0)
        out = {}
        for i, ch in enumerate(self.col_range):
            out[ch] = {
                "mae_train": float(MAE(y_train.iloc[:, i], pred_train[:, i])),
                "mae_test": float(MAE(y_test.iloc[:, i], pred_test[:, i])),
                "meae_train": float(MeAE(y_train.iloc[:, i], pred_train[:, i])),
                "meae_test": float(MeAE(y_test.iloc[:, i], pred_test[:, i])),
            }
        return out

    # ---------------------------------------------------------------- bundles
    def save_bundle(self, bundle_dir: Path, model_file: str = "model.keras") -> None:
        bundle_dir = Path(bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        if not (bundle_dir / model_file).exists():
            self.nn_r.save(str(bundle_dir / model_file))
        joblib.dump(self.scaler, bundle_dir / "scaler.joblib")
        meta = dict(self.metadata)
        meta.update({
            "model_file": model_file,
            "period": {"start_date": self.start_date, "end_date": self.end_date},
            "n_rows_outside_saa": int(len(self.df_data)) if self.df_data is not None else None,
            "n_rows_training_pool": int(self.index_date.sum()) if self.index_date is not None else None,
            "features": self.col_selected,
            "targets": self.col_range,
            "versions": {"python": platform.python_version(), "tensorflow": tf.__version__,
                         "keras": tf.keras.__version__ if hasattr(tf.keras, "__version__") else None,
                         "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__},
        })
        (bundle_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self.metadata = meta
        logging.info(f"Model bundle saved to {bundle_dir}")

    def load_bundle(self, bundle_dir: Path) -> None:
        """Loads network, scaler and metadata saved together."""
        bundle_dir = Path(bundle_dir)
        self.metadata = json.loads((bundle_dir / "metadata.json").read_text(encoding="utf-8"))
        self.nn_r = load_model(str(bundle_dir / self.metadata["model_file"]), compile=False,
                               custom_objects={"loss_median": loss_median, "loss_max": loss_max})
        self.scaler = joblib.load(bundle_dir / "scaler.joblib")
        logging.info(f"Loaded model bundle {bundle_dir.name} (source: {self.metadata.get('source')})")

    def bundle_from_legacy_h5(self, h5_path: Path, bundle_dir: Path) -> None:
        """
        Wraps a model trained by the upstream code (which did not save its scaler) into a bundle.
        The scaler is refitted on the same deterministic training split; prepare() must have run
        on the same period and inputs used for training.
        """
        h5_path, bundle_dir = Path(h5_path), Path(bundle_dir)
        self.nn_r = load_model(str(h5_path), compile=False, custom_objects={"loss_median": loss_median, "loss_max": loss_max})
        self.fit_scaler()
        bundle_dir.mkdir(parents=True, exist_ok=False)
        shutil.copy2(h5_path, bundle_dir / "model.h5")
        self.metadata = {"source": "legacy_h5", "legacy_file": h5_path.name,
                         "note": "trained by upstream-equivalent code (b0b2802); scaler refitted with split_seed",
                         "split_seed": SPLIT_SEED}
        self.save_bundle(bundle_dir, model_file="model.h5")

    # -------------------------------------------------------------- inference
    def predict(self, frg_path: Path, bkg_path: Path, time_to_del: int = 150) -> Tuple[Path, Path]:
        """
        Predicts the background on every row outside SAA and writes two new files:
        frg (observed rates) and bkg (predicted rates), both with 'met' and UTC 'timestamp'.
        Rows within time_to_del bins of a gap > 500 s and zero-count cells are set to NaN in both.
        """
        frg_path, bkg_path = Path(frg_path), Path(bkg_path)
        for p in (frg_path, bkg_path):
            if p.exists():
                raise FileExistsError(f"Refusing to overwrite {p}")
            p.parent.mkdir(parents=True, exist_ok=True)

        X_all = self.scaler.transform(self.df_data[self.col_selected].astype("float32"))
        y_pred_arr = self.nn_r.predict(X_all, batch_size=8192, verbose=0)

        met = self.df_data["met"].to_numpy()
        ts = met_to_utc(met)

        df_ori = self.df_data[self.col_range].astype("float32").reset_index(drop=True)
        y_pred = pd.DataFrame(y_pred_arr, columns=self.col_range)

        if time_to_del > 0:
            rows = saa_mask_indices(met, time_to_del)
            df_ori.loc[rows, self.col_range] = np.nan
            y_pred.loc[rows, self.col_range] = np.nan
            logging.info(f"Masked {len(rows)} rows within {time_to_del} bins of SAA gaps")

        zeros = (df_ori[self.col_range] == 0).to_numpy()
        df_ori = df_ori.mask(zeros)
        y_pred = y_pred.mask(zeros)
        logging.info(f"Masked {int(zeros.sum())} zero-count cells")
        if (y_pred[self.col_range] == 0).any().any():
            logging.error(f"Predicted rate equal to 0 in {int((y_pred[self.col_range] == 0).to_numpy().sum())} cells")

        for df in (df_ori, y_pred):
            df["met"] = met
            df["timestamp"] = ts.values
        df_ori.to_csv(frg_path, index=False)
        y_pred.to_csv(bkg_path, index=False)
        logging.info(f"Wrote {frg_path} and {bkg_path}")
        return frg_path, bkg_path
