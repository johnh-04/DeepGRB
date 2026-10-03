"""
DeepGRB pipeline, steps 1-5 (Crupi et al. 2023 engine).

1. download CSPEC + POSHIST for START_DATE..END_DATE (idempotent)
2. preprocess daily tables (only days still missing)
3. neural background: model bundle -> run_dir/pred/{frg,bkg}.csv
4. Poisson-FOCuS -> run_dir/trig/{trig,offset}.csv
5. triggers and events -> run_dir/results/{triggers_table,events_table}.csv

Every step of 3-5 is skipped when its outputs already exist in run_dir, which is
keyed by period and ENGINE_VERSION (connections/utils/config.py). Inputs are never
overwritten. Validation (Phase 3) and classification (Phase 4) run separately.

Usage (from repo root):  python pipeline/pipeline_bkg.py
"""

import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import tensorflow as tf

from connections.utils.config import (
    DATA_DIR,
    END_DATE,
    ENGINE_VERSION,
    FOLD_BKG,
    FOLD_CSPEC_POS,
    FOLD_NN,
    FOLD_POSHIST,
    GBM_TRIG_DB,
    START_DATE,
    run_dir,
)
from models.analyze import BINLENGTH, MAX_DET_NUMBER, MERGE_SECONDS, MIN_DET_NUMBER, EventAnalyzer
from models.download_bkg import download_days
from models.model_nn import ModelNN
from models.preprocess import build_table
from models.trigger import run_trigger
from models.trigs.focus import build_focus_runner

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

# ----------------------------------------------------------------------
# Parameters (paper / upstream code; see docs/WORKING_RULES.md §2 for the decisions)
# ----------------------------------------------------------------------
ERANGE = {"n": [(28, 50), (50, 300), (300, 500)], "b": [(756, 5025), (5025, 50000)]}
NN_PARAMS = {"loss_type": "mean", "units": 2048, "epochs": 64, "lr": 0.0008, "bs": 2048, "dropout_rate": 0.02}
TRAIN_SEED = 0
TIME_TO_DEL_BINS = 150  # upstream: 150 bins (~614 s) each side of a > 500 s gap
FOCUS_MU_MIN = 1.2
FOCUS_T_MAX = 50  # bins (204.8 s), as upstream
ANALYZE_THRESHOLD = 3.0  # sigma, range r1

# Background model: one network per period (paper). For the 2019 baseline period the
# paper-faithful model trained on 2026-09-21 by upstream-equivalent code is reused.
LEGACY_PERIOD = ("2019-03-01", "2019-06-30")
LEGACY_H5 = DATA_DIR / FOLD_NN / "model_03-2019_07-2019_4.4_2026-09-21.h5"
if (START_DATE, END_DATE) == LEGACY_PERIOD:
    MODEL_BUNDLE = DATA_DIR / FOLD_NN / "bundles" / LEGACY_H5.stem
else:
    MODEL_BUNDLE = DATA_DIR / FOLD_NN / "bundles" / f"model_{START_DATE}_{END_DATE}_seed{TRAIN_SEED}"
# A new (long) training must be explicitly enabled: DEEPGRB_ALLOW_TRAINING=1
ALLOW_TRAINING = os.environ.get("DEEPGRB_ALLOW_TRAINING") == "1"

cspec_dir = DATA_DIR / FOLD_CSPEC_POS
poshist_dir = DATA_DIR / FOLD_POSHIST
bkg_dir = DATA_DIR / FOLD_BKG
RUN = run_dir()
PRED_FRG, PRED_BKG = RUN / "pred" / "frg.csv", RUN / "pred" / "bkg.csv"
TRIG, OFFSET = RUN / "trig" / "trig.csv", RUN / "trig" / "offset.csv"
RESULTS = RUN / "results"


def parameters() -> dict:
    return {
        "period": {"start_date": START_DATE, "end_date": END_DATE},
        "engine_version": ENGINE_VERSION,
        "bin_length_s": BINLENGTH,
        "energy_ranges_keV": ERANGE,
        "nn": NN_PARAMS,
        "train_seed": TRAIN_SEED,
        "model_bundle": str(MODEL_BUNDLE.relative_to(REPO_ROOT)),
        "saa_gap_s": 500,
        "saa_exclusion_bins_each_side": TIME_TO_DEL_BINS,
        "focus": {"mu_min": FOCUS_MU_MIN, "t_max_bins": FOCUS_T_MAX, "input": "rates (counts/s)"},
        "trigger": {"threshold_sigma": ANALYZE_THRESHOLD, "range": "r1", "min_detectors": MIN_DET_NUMBER,
                    "max_detectors_exclusive": MAX_DET_NUMBER},
        "merge_s": MERGE_SECONDS,
        "significance": "S=sum(N-B)/sqrt(sum(B)), triggered detectors, offset-extended interval, max over 21 quantile cuts",
    }


def write_manifest() -> None:
    """Prints the parameters and records them, with code version, in run_dir/manifest.json."""
    params = parameters()
    for line in json.dumps(params, indent=2).splitlines():
        logging.info(f"[params] {line}")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "models", "pipeline", "connections", "utils"],
                                    cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip())
    except OSError:
        commit, dirty = "unknown", True
    RUN.mkdir(parents=True, exist_ok=True)
    manifest_path = RUN / "manifest.json"
    history = json.loads(manifest_path.read_text())["runs"] if manifest_path.exists() else []
    history.append({"started": pd.Timestamp.now(tz="UTC").isoformat(), "git_commit": commit, "code_dirty": dirty,
                    "versions": {"python": platform.python_version(), "tensorflow": tf.__version__,
                                 "numpy": np.__version__, "pandas": pd.__version__}})
    manifest_path.write_text(json.dumps({"parameters": params, "runs": history}, indent=2))
    if dirty:
        logging.warning("Engine code has uncommitted changes: results are not tied to a commit.")


def run_step_download() -> pd.DataFrame:
    print(f"\n[STEP 1/5] Download ({START_DATE} to {END_DATE}, inclusive)")
    df_days = download_days(START_DATE, END_DATE, cspec_dir=cspec_dir, poshist_dir=poshist_dir)
    logging.info(f"Raw data complete for {int(df_days['complete'].sum())}/{len(df_days)} days.")
    return df_days


def run_step_preprocess(df_days: pd.DataFrame) -> None:
    print(f"\n[STEP 2/5] Preprocess into {bkg_dir}")
    todo = df_days[df_days["complete"] & ~df_days["day"].apply(lambda d: (bkg_dir / f"{d}.csv").exists())]
    if todo.empty:
        logging.info("All complete days already have a preprocessed table.")
        return
    logging.info(f"Preprocessing {len(todo)} new day(s): {', '.join(todo['day'])}")
    build_table(todo, ERANGE, bool_overwrite=False, bool_parallel=True, n_jobs=4)


def run_step_neural_network() -> None:
    print(f"\n[STEP 3/5] Neural background -> {PRED_FRG.parent}")
    if PRED_FRG.exists() and PRED_BKG.exists():
        logging.info("Background predictions already in this run folder. Skipping.")
        return
    if PRED_FRG.exists() or PRED_BKG.exists():
        raise RuntimeError(f"Incomplete step 3 outputs in {PRED_FRG.parent}: move them to an archive and rerun.")

    nn = ModelNN(START_DATE, END_DATE, bkg_dir=bkg_dir, trig_catalog_path=GBM_TRIG_DB)
    nn.prepare(bool_del_trig=True)
    if MODEL_BUNDLE.exists():
        nn.load_bundle(MODEL_BUNDLE)
    elif (START_DATE, END_DATE) == LEGACY_PERIOD and LEGACY_H5.exists():
        logging.info(f"Wrapping legacy model {LEGACY_H5.name} into a bundle (scaler refitted, split seed fixed).")
        nn.bundle_from_legacy_h5(LEGACY_H5, MODEL_BUNDLE)
    elif ALLOW_TRAINING:
        nn.train(MODEL_BUNDLE, seed=TRAIN_SEED, **NN_PARAMS)
    else:
        raise RuntimeError(f"No model bundle {MODEL_BUNDLE.name}: set DEEPGRB_ALLOW_TRAINING=1 to train one.")
    nn.predict(PRED_FRG, PRED_BKG, time_to_del=TIME_TO_DEL_BINS)


def run_step_trigger() -> None:
    print(f"\n[STEP 4/5] Poisson-FOCuS -> {TRIG.parent}")
    if TRIG.exists() and OFFSET.exists():
        logging.info("FOCuS outputs already in this run folder. Skipping.")
        return
    focus = run_trigger(PRED_FRG, PRED_BKG, TRIG, OFFSET, build_focus_runner(mu_min=FOCUS_MU_MIN, t_max=FOCUS_T_MAX))
    logging.info(f"Max significance {np.nanmax(focus.to_numpy()):.2f} sigma; "
                 f"bins with r1 > {ANALYZE_THRESHOLD} sigma on some detector: "
                 f"{int((focus.filter(like='_r1') > ANALYZE_THRESHOLD).any(axis=1).sum())}")


def run_step_analyze() -> pd.DataFrame:
    print(f"\n[STEP 5/5] Triggers and events -> {RESULTS}")
    events_csv = RESULTS / "events_table.csv"
    if events_csv.exists():
        logging.info("Event table already in this run folder. Skipping.")
        return pd.read_csv(events_csv)
    analyzer = EventAnalyzer(PRED_FRG, PRED_BKG, TRIG, OFFSET, GBM_TRIG_DB)
    _, events = analyzer.run(ANALYZE_THRESHOLD, RESULTS)
    logging.info(f"Events: {len(events)}; CE tiers: {events['CE'].value_counts().to_dict()}")
    return events


if __name__ == "__main__":
    print("=" * 65)
    print(f"  DEEPGRB ENGINE {START_DATE} -> {END_DATE}  (engine v{ENGINE_VERSION})")
    print(f"  run folder: {RUN}")
    print("=" * 65)
    write_manifest()
    df_days = run_step_download()
    run_step_preprocess(df_days)
    run_step_neural_network()
    run_step_trigger()
    run_step_analyze()
    print("\nSteps 1-5 completed. Validation: Phase 3 (benchmark/validate.py).")
