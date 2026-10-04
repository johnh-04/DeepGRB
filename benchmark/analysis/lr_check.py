"""
Read-only check for the learning-rate question (docs/WORKLOG.md, 2026-10-04).

Computes, on the same training pool and deterministic split used by ModelNN.train, the MAE of
trivial predictors: always 0 (what a network with all ReLU outputs at zero returns) and the
per-channel mean/median of the fit subset. These are the loss levels to compare with the
first epochs of the training log.

Usage (repo root): python -m benchmark.analysis.lr_check
"""

import json
from pathlib import Path

import numpy as np

from connections.utils.config import BASE_DIR, END_DATE, START_DATE
from models.model_nn import ModelNN

OUT = BASE_DIR / "benchmark" / "analysis" / "out"


def main() -> None:
    nn = ModelNN(START_DATE, END_DATE)
    nn.prepare(bool_del_trig=True)
    X_train, X_test, y_train, y_test = nn._split()
    n_fit = int(len(X_train) * (1 - 0.3))  # Keras validation_split takes the last 30%
    y_fit, y_val = y_train.iloc[:n_fit].to_numpy(), y_train.iloc[n_fit:].to_numpy()

    def mae(y, pred):
        return float(np.mean(np.abs(y - pred)))

    res = {
        "rows_fit": int(len(y_fit)), "rows_validation": int(len(y_val)),
        "mae_zero_fit": mae(y_fit, 0.0), "mae_zero_validation": mae(y_val, 0.0),
        "mae_channel_mean_fit": mae(y_fit, y_fit.mean(axis=0)), "mae_channel_median_fit": mae(y_fit, np.median(y_fit, axis=0)),
        "mae_channel_median_validation": mae(y_val, np.median(y_fit, axis=0)),
        "mean_target_rate_fit": float(y_fit.mean()),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lr_check.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
