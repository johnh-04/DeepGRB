"""
Read-only diagnosis of the bins where the network of a run predicts a background <= 0.

For every such bin and its 5 neighbours on each side:
  - the 60 network inputs (raw and standardised with the bundle's scaler), NaN check,
    percentile rank of each input in the whole period, jump from the previous bin
    compared with the typical bin-to-bin change of that input;
  - the network output, the pre-activation of the final ReLU layer and the prediction of the
    comparison run's network on the same bins;
  - sensitivity: each input of a zero bin is replaced by the mean of its non-zero
    neighbours; the inputs whose replacement makes the output positive are listed.

Outputs in <run>/analysis/: zero_prediction_bins.csv, zero_prediction_inputs.csv,
zero_prediction_sensitivity.csv, zero_prediction_summary.json (read by orbit_report.py).
Usage (repo root): python -m benchmark.analysis.zero_prediction --run <run> --compare <comparison run>
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

import benchmark.analysis.orbit_analysis as oa
from connections.utils.config import BASE_DIR
from models.model_nn import ModelNN
from utils.keys import get_keys
from utils.logs import detail, setup_logging
from utils.run_options import manifest_model, read_manifest

NEIGHBOURS = 5


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    oa.add_cli(parser)
    args = parser.parse_args()
    setup_logging()
    oa.configure(args.run, args.compare)
    OUT, RUNS = oa.OUT, oa.RUNS
    bundle = BASE_DIR / manifest_model(read_manifest(RUNS["ref"]["run"]))["bundle"]
    OUT.mkdir(parents=True, exist_ok=True)
    keys = get_keys()
    bkg_ref = pd.read_csv(RUNS["ref"]["run"] / "pred" / "bkg.csv", usecols=keys)
    bkg_cmp = pd.read_csv(RUNS["cmp"]["run"] / "pred" / "bkg.csv", usecols=keys)
    frg = pd.read_csv(RUNS["ref"]["run"] / "pred" / "frg.csv", usecols=["met", "timestamp"])
    zero_rows = np.where((bkg_ref.to_numpy() <= 0).any(axis=1))[0]

    nn = ModelNN(oa.START_DATE, oa.END_DATE)
    nn.prepare(bool_del_trig=True)
    nn.load_bundle(bundle)
    feats = nn.col_selected
    X_raw = nn.df_data[feats].astype("float32")
    assert np.allclose(nn.df_data["met"].to_numpy(), frg["met"].to_numpy()), "row alignment with pred/ failed"
    scale_mean, scale_std = nn.scaler.mean_, nn.scaler.scale_

    rows = sorted({r for z in zero_rows for r in range(z - NEIGHBOURS, z + NEIGHBOURS + 1) if 0 <= r < len(X_raw)})
    Xs = nn.scaler.transform(X_raw.iloc[rows])

    # network output and pre-activation of the final (ReLU) Dense layer
    model = nn.nn_r
    last = model.layers[-1]
    penult = tf.keras.Model(inputs=model.inputs, outputs=model.layers[-2].output)
    h = penult.predict(Xs, verbose=0)
    W, b = last.get_weights()
    pre = h @ W + b
    out = model.predict(Xs, verbose=0)

    # typical bin-to-bin change of each input (consecutive rows less than 10 s apart)
    met = nn.df_data["met"].to_numpy()
    consecutive = np.r_[False, np.diff(met) < 10]
    dX = np.abs(np.diff(X_raw.to_numpy(), axis=0, prepend=np.nan))
    typical_jump = np.nanmedian(dX[consecutive], axis=0)
    p999_jump = np.nanpercentile(dX[consecutive], 99.9, axis=0)

    bins = []
    for k, r in enumerate(rows):
        z = (X_raw.iloc[r].to_numpy() - scale_mean) / scale_std
        jump = dX[r] / np.where(p999_jump > 0, p999_jump, np.nan)
        bins.append({
            "row": r, "timestamp": frg.at[r, "timestamp"], "met": met[r], "zero_bin": r in set(zero_rows),
            "dt_prev_s": met[r] - met[r - 1] if r > 0 else np.nan,
            "n_nan_inputs": int(np.isnan(X_raw.iloc[r].to_numpy()).sum()),
            "max_abs_z": float(np.nanmax(np.abs(z))), "feature_max_abs_z": feats[int(np.nanargmax(np.abs(z)))],
            "max_jump_over_p999": float(np.nanmax(jump)) if np.isfinite(jump).any() else np.nan,
            "feature_max_jump": feats[int(np.nanargmax(jump))] if np.isfinite(jump).any() else "",
            "ref_pred_sum_r1": float(bkg_ref.loc[r, [c for c in keys if c.endswith("_r1")]].sum()),
            "ref_channels_le0": int((bkg_ref.loc[r] <= 0).sum()),
            "cmp_pred_sum_r1": float(bkg_cmp.loc[r, [c for c in keys if c.endswith("_r1")]].sum()),
            "network_out_sum": float(out[k].sum()), "preact_max": float(pre[k].max()), "preact_median": float(np.median(pre[k])),
            "penultimate_mean_abs": float(np.mean(np.abs(h[k]))),
        })
    bins = pd.DataFrame(bins)
    bins.to_csv(OUT / "zero_prediction_bins.csv", index=False)

    # inputs of the zero bins vs. their neighbours and the whole period
    inp = []
    all_vals = X_raw.to_numpy()
    for r in zero_rows:
        nb = [q for q in range(r - NEIGHBOURS, r + NEIGHBOURS + 1) if 0 <= q < len(X_raw) and q not in set(zero_rows)]
        for j, f in enumerate(feats):
            v = float(X_raw.iat[r, j])
            col = all_vals[:, j]
            inp.append({"row": r, "feature": f, "value": v, "z": (v - scale_mean[j]) / scale_std[j],
                        "percentile_in_period": float(100 * np.mean(col <= v)),
                        "neighbours_mean": float(np.mean(all_vals[nb, j])), "jump_prev_over_p999": float(dX[r, j] / p999_jump[j]) if p999_jump[j] > 0 else np.nan})
    inp = pd.DataFrame(inp)
    inp.to_csv(OUT / "zero_prediction_inputs.csv", index=False)

    # sensitivity: replace one standardised input at a time by the neighbours' mean
    sens = []
    for r in zero_rows:
        nb = [q for q in range(r - NEIGHBOURS, r + NEIGHBOURS + 1) if 0 <= q < len(X_raw) and q not in set(zero_rows)]
        x0 = nn.scaler.transform(X_raw.iloc[[r]])
        xn = nn.scaler.transform(X_raw.iloc[nb]).mean(axis=0)
        trial = np.repeat(x0, len(feats), axis=0)
        trial[np.arange(len(feats)), np.arange(len(feats))] = xn
        o = model.predict(trial, verbose=0).sum(axis=1)
        all_nb = model.predict(xn[None, :], verbose=0).sum()
        for j, f in enumerate(feats):
            sens.append({"row": r, "feature": f, "out_sum_after_replacing": float(o[j]), "out_sum_all_inputs_from_neighbours": float(all_nb)})
    sens = pd.DataFrame(sens)
    sens.to_csv(OUT / "zero_prediction_sensitivity.csv", index=False)

    zb = bins[bins["zero_bin"]]
    nz = bins[~bins["zero_bin"]]
    restoring = sens[sens["out_sum_after_replacing"] > 0].groupby("feature")["row"].nunique().sort_values(ascending=False)
    summary = {
        "zero_rows": [int(r) for r in zero_rows], "zero_timestamps": zb["timestamp"].tolist(),
        "cells": int((bkg_ref.to_numpy() <= 0).sum()),
        "nan_inputs_in_zero_bins": int(zb["n_nan_inputs"].sum()),
        "max_abs_z_zero_bins": float(zb["max_abs_z"].max()), "max_abs_z_neighbours": float(nz["max_abs_z"].max()),
        "max_jump_over_p999_zero_bins": float(zb["max_jump_over_p999"].max()),
        "max_jump_over_p999_neighbours": float(nz["max_jump_over_p999"].max()),
        "preact_max_zero_bins": float(zb["preact_max"].max()), "preact_max_neighbours_min": float(nz["preact_max"].min()),
        "cmp_pred_sum_r1_zero_bins": [float(v) for v in zb["cmp_pred_sum_r1"]],
        "features_restoring_output": {f: int(n) for f, n in restoring.items()},
        "neighbour_mean_input_output_positive": bool((sens.groupby("row")["out_sum_all_inputs_from_neighbours"].first() > 0).all()),
    }
    (OUT / "zero_prediction_summary.json").write_text(json.dumps(summary, indent=2))
    detail(f"written {OUT}: {len(zero_rows)} zero-prediction bins, {summary['cells']} cells")


if __name__ == "__main__":
    main()
