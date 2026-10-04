"""
DeepGRB pipeline, steps 1-5 (Crupi et al. 2023 engine).

1. download CSPEC + POSHIST for START_DATE..END_DATE (idempotent)
2. preprocess daily tables (only days still missing)
3. neural background: model bundle -> run_dir/pred/{frg,bkg}.csv
4. Poisson-FOCuS -> run_dir/trig/{trig,offset}.csv
5. triggers and events -> run_dir/results/{triggers_table,events_table}.csv

Default run: every step of 3-5 is skipped when its outputs already exist in run_dir,
which is keyed by period and ENGINE_VERSION (connections/utils/config.py).
Labelled run (DEEPGRB_RUN_LABEL): a new folder run_dir-<label> and a new model bundle;
both must not exist yet. Inputs are never overwritten. Options: utils/run_options.py;
DEEPGRB_SKIP_DOWNLOAD=1 skips steps 1-2 after checking that all daily tables exist.
Validation (Phase 3) and classification (Phase 4) run separately.

Usage (from repo root):  python -u pipeline/pipeline_bkg.py
Retraining 2019 (example):
  DEEPGRB_RUN_LABEL=seed1 DEEPGRB_TRAIN_SEED=1 DEEPGRB_FORCE_TRAIN=1 DEEPGRB_SKIP_DOWNLOAD=1 \
      python -u pipeline/pipeline_bkg.py
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
    PRED_TRIG_COMPATIBLE_SINCE,
    START_DATE,
    run_dir,
)
from models.analyze import BINLENGTH, MAX_DET_NUMBER, MERGE_SECONDS, MIN_DET_NUMBER, EventAnalyzer
from models.download_bkg import download_days
from models.model_nn import ModelNN, count_nonpositive_predictions
from models.preprocess import build_table
from models.trigger import run_trigger
from models.trigs.focus import build_focus_runner
from utils.period import window_days
from utils.run_options import RunOptionsError, obtain_model, resolve_run_options

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

# ----------------------------------------------------------------------
# Parameters (paper / upstream code; see docs/WORKING_RULES.md §2 for the decisions)
# ----------------------------------------------------------------------
ERANGE = {"n": [(28, 50), (50, 300), (300, 500)], "b": [(756, 5025), (5025, 50000)]}
NN_PARAMS = {"loss_type": "mean", "units": 2048, "epochs": 64, "lr": 0.0008, "bs": 2048, "dropout_rate": 0.02}
TIME_TO_DEL_BINS = 150  # upstream: 150 bins (~614 s) each side of a > 500 s gap
FOCUS_MU_MIN = 1.2
FOCUS_T_MAX = 50  # bins (204.8 s), as upstream
ANALYZE_THRESHOLD = 3.0  # sigma, range r1

# Background model: one network per period (paper). Without a run label, the 2019 baseline
# period reuses the paper-faithful model trained on 2026-09-21 by upstream-equivalent code;
# labelled runs (utils/run_options.py) train or reuse their own bundle and never use it.
try:
    _reuse = run_dir(engine_version=PRED_TRIG_COMPATIBLE_SINCE) if PRED_TRIG_COMPATIBLE_SINCE != ENGINE_VERSION else None
    OPTS = resolve_run_options(os.environ, START_DATE, END_DATE, run_dir(), DATA_DIR / FOLD_NN, reuse_source_dir=_reuse)
except RunOptionsError as e:
    if __name__ == "__main__":
        sys.exit(f"[run options] {e}")
    raise
SKIP_DOWNLOAD = os.environ.get("DEEPGRB_SKIP_DOWNLOAD") == "1"
TRAIN_SEED = OPTS.seed
MODEL_BUNDLE = OPTS.bundle_dir

cspec_dir = DATA_DIR / FOLD_CSPEC_POS
poshist_dir = DATA_DIR / FOLD_POSHIST
bkg_dir = DATA_DIR / FOLD_BKG
RUN = OPTS.run_dir
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
        "run_label": OPTS.label,
        "model_bundle": str(MODEL_BUNDLE.relative_to(REPO_ROOT) if MODEL_BUNDLE.is_absolute() else MODEL_BUNDLE),
        "model_mode": OPTS.mode,
        "force_train": OPTS.force_train,
        "saa_gap_s": 500,
        "saa_exclusion_bins_each_side": TIME_TO_DEL_BINS,
        "focus": {"mu_min": FOCUS_MU_MIN, "t_max_bins": FOCUS_T_MAX, "input": "rates (counts/s)"},
        "trigger": {"threshold_sigma": ANALYZE_THRESHOLD, "range": "r1", "min_detectors": MIN_DET_NUMBER,
                    "max_detectors_exclusive": MAX_DET_NUMBER},
        "merge_s": MERGE_SECONDS,
        "significance": "S=sum(N-B)/sqrt(sum(B)), triggered detectors, offset-extended interval, max over 21 quantile cuts",
    }


def git_state() -> tuple:
    """(commit, engine code dirty) of the working tree."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "models", "pipeline", "connections", "utils"],
                                    cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip())
    except OSError:
        commit, dirty = "unknown", True
    return commit, dirty


def update_manifest(key: str, value) -> None:
    """Adds or replaces one top-level entry of run_dir/manifest.json."""
    path = RUN / "manifest.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[key] = value
    path.write_text(json.dumps(data, indent=2))


def record_predicted_zero(how: str) -> None:
    """Counts predicted background <= 0 (invalid for FOCuS and S) and stores it in the manifest."""
    counts = count_nonpositive_predictions(PRED_BKG)
    counts["source"] = how
    update_manifest("predicted_zero_cells", counts)
    logging.info(f"Predicted background <= 0: {counts['cells']} cells, {counts['bins_all_channels']} whole bins ({how})")


def report_devices() -> None:
    """Prints the GPUs seen by TensorFlow, or a warning that training would run on CPU."""
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                logging.warning(f"Could not enable memory growth on {gpu.name}: {e}")
        print(f"[devices] GPU detected: {', '.join(g.name for g in gpus)}", flush=True)
    else:
        print("[devices] WARNING: no GPU detected by TensorFlow; "
              + ("TRAINING WILL RUN ON CPU (much slower)." if OPTS.mode == "train" else "inference runs on CPU."),
              flush=True)


def write_manifest() -> None:
    """Prints the parameters and records them, with code version, in run_dir/manifest.json."""
    params = parameters()
    for line in json.dumps(params, indent=2).splitlines():
        logging.info(f"[params] {line}")
    commit, dirty = git_state()
    if OPTS.is_labelled:
        RUN.mkdir(parents=True, exist_ok=False)  # labelled runs never reuse a folder
    else:
        RUN.mkdir(parents=True, exist_ok=True)
    manifest_path = RUN / "manifest.json"
    history = json.loads(manifest_path.read_text())["runs"] if manifest_path.exists() else []
    history.append({"started": pd.Timestamp.now(tz="UTC").isoformat(), "git_commit": commit, "code_dirty": dirty,
                    "versions": {"python": platform.python_version(), "tensorflow": tf.__version__,
                                 "numpy": np.__version__, "pandas": pd.__version__}})
    manifest_path.write_text(json.dumps({"parameters": params, "runs": history}, indent=2))
    if dirty:
        logging.warning("Engine code has uncommitted changes: results are not tied to a commit.")


def check_daily_tables() -> None:
    """With DEEPGRB_SKIP_DOWNLOAD=1: no download/preprocess, but every day must have its table."""
    print(f"\n[STEP 1-2/5] Skipped (DEEPGRB_SKIP_DOWNLOAD=1): checking daily tables in {bkg_dir}", flush=True)
    missing = [d for d in window_days(START_DATE, END_DATE) if not (bkg_dir / f"{d}.csv").exists()]
    if missing:
        sys.exit(f"[STEP 1-2/5] {len(missing)} daily table(s) missing ({', '.join(missing[:10])}"
                 f"{' ...' if len(missing) > 10 else ''}): run without DEEPGRB_SKIP_DOWNLOAD.")
    logging.info(f"All {len(window_days(START_DATE, END_DATE))} daily tables present.")


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
    if OPTS.mode == "reuse_pred":
        src = OPTS.reuse_source
        for sub in ("pred", "trig"):
            if not (RUN / sub).exists():
                (RUN / sub).symlink_to(src / sub, target_is_directory=True)
        src_manifest = json.loads((src / "manifest.json").read_text()) if (src / "manifest.json").exists() else {}
        update_manifest("reused_from", {
            "run": str(src.relative_to(REPO_ROOT)), "engine_version": PRED_TRIG_COMPATIBLE_SINCE, "how": "symlink",
            "steps": ["3 pred/", "4 trig/"],
            "model_bundle": src_manifest.get("parameters", {}).get("model_bundle"),
            "source_git_commit": (src_manifest.get("runs") or [{}])[0].get("git_commit"),
        })
        logging.info(f"Reusing pred/ and trig/ of {src} (symlinks); steps 3-4 are unchanged since engine v{PRED_TRIG_COMPATIBLE_SINCE}.")
        record_predicted_zero(f"reused from {src.name}")
        return
    if PRED_FRG.exists() and PRED_BKG.exists():
        logging.info("Background predictions already in this run folder. Skipping.")
        return
    if PRED_FRG.exists() or PRED_BKG.exists():
        raise RuntimeError(f"Incomplete step 3 outputs in {PRED_FRG.parent}: move them to an archive and rerun.")

    nn = ModelNN(START_DATE, END_DATE, bkg_dir=bkg_dir, trig_catalog_path=GBM_TRIG_DB)
    nn.prepare(bool_del_trig=True)
    logging.info(f"Model mode: {OPTS.mode} -> {MODEL_BUNDLE}")
    commit, dirty = git_state()
    obtain_model(nn, OPTS, NN_PARAMS, extra_metadata={
        "git_commit": commit, "code_dirty": dirty, "run_label": OPTS.label, "run_dir": str(RUN.relative_to(REPO_ROOT)),
        "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
    })
    nn.predict(PRED_FRG, PRED_BKG, time_to_del=TIME_TO_DEL_BINS)
    record_predicted_zero("predicted in this run")


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
    print(f"  model: {OPTS.mode} {MODEL_BUNDLE.name}  (seed {TRAIN_SEED}, label {OPTS.label})", flush=True)
    report_devices()
    write_manifest()
    if SKIP_DOWNLOAD:
        check_daily_tables()
    else:
        df_days = run_step_download()
        run_step_preprocess(df_days)
    run_step_neural_network()
    run_step_trigger()
    run_step_analyze()
    print("\nSteps 1-5 completed. Validation: Phase 3 (benchmark/validate.py).")
