"""
pipeline_start.py - verification run of the DeepGRB pipeline, from step 3 to step 9.

What it does
  * Reuses the daily tables of steps 1-2 (no download, no preprocessing).
  * Copies the reference network bundle into a NEW bundle folder (the original is never touched).
  * Runs the real pipeline (pipeline/pipeline_bkg.py) in a NEW run folder, so nothing exists yet and
    every step executes: 3 background network, 4 FOCuS, 5 events, 6 localization + classification,
    7 flags, 8 validation (GBM catalog + Crupi's tables), 9 report.
  * Never trains a network and never overwrites the baseline run.

Usage (from the repo root), always with a NEW label:
    python -u pipeline/pipeline_start.py --dry-run          # show what would run, write nothing
    nohup python -u pipeline/pipeline_start.py > logs/verify1.out 2>&1 &

Results: data/runs/<START>_<END>/engine-v<N>-<NEW_LABEL>/RESULTS.md and validation/*.csv
"""

# ================================ SETTINGS ================================
START_DATE = "2019-03-01"                                # first UTC day, included
END_DATE = "2019-06-30"                                  # last UTC day, included
BUNDLE_TO_REUSE = "model_2019-03-01_2019-06-30_seed1"    # folder in data/nn_model/bundles/
NEW_LABEL = "verify1"                                    # NEW every time: names the run and the bundle copy
JOBS = 4                                                 # parallel jobs (localization)
# ==========================================================================

import importlib.util
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)

BUNDLES = REPO_ROOT / "data" / "nn_model" / "bundles"
NEW_BUNDLE = BUNDLES / f"model_{START_DATE}_{END_DATE}_{NEW_LABEL}"


def main() -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from utils.logs import log, setup_logging
    setup_logging()
    dry_run = "--dry-run" in sys.argv[1:]
    source = BUNDLES / BUNDLE_TO_REUSE
    if not source.is_dir():
        log.error(f"[pipeline_start] bundle not found: {source}")
        return 2
    if NEW_BUNDLE.exists():
        log.info(f"[pipeline_start] bundle copy already present: {NEW_BUNDLE.name}")
    elif dry_run:
        log.info(f"[pipeline_start] dry run: would copy {source.name} -> {NEW_BUNDLE.name}")
    else:
        shutil.copytree(source, NEW_BUNDLE)
        log.info(f"[pipeline_start] bundle copied: {source.name} -> {NEW_BUNDLE.name}")

    os.environ.update({
        "DEEPGRB_START_DATE": START_DATE,
        "DEEPGRB_END_DATE": END_DATE,
        "DEEPGRB_RUN_LABEL": NEW_LABEL,
        "DEEPGRB_REUSE_BUNDLE": "1",     # load the (copied) bundle, never train
        "DEEPGRB_SKIP_DOWNLOAD": "1",    # steps 1-2 already done
        "DEEPGRB_JOBS": str(JOBS),
    })
    os.environ.pop("DEEPGRB_FORCE_TRAIN", None)
    os.environ.pop("DEEPGRB_ALLOW_TRAINING", None)

    spec = importlib.util.spec_from_file_location("pipeline_bkg", REPO_ROOT / "pipeline" / "pipeline_bkg.py")
    pipeline = importlib.util.module_from_spec(spec)
    sys.modules["pipeline_bkg"] = pipeline
    spec.loader.exec_module(pipeline)
    return pipeline.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())