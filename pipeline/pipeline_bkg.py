"""
DeepGRB pipeline (Crupi et al. 2023), the single entry point.

  1. download CSPEC + POSHIST of the period (idempotent)
  2. preprocess daily tables -> data/bkg/YYMMDD.csv
  3. neural background -> <run>/pred/{frg,bkg}.csv
  4. Poisson-FOCuS -> <run>/trig/{trig,offset}.csv
  5. triggers and events -> <run>/results/{triggers_table,events_table}.csv
  6. localization (PSO, slow) + Crupi's heuristic classification -> results/events_table_loc.csv, events_classified.csv
  7. post-processing flags -> results/events_flags.csv
  8. validation against the GBM catalog (always) and Crupi's tables (2019 only) -> <run>/validation/
  9. report -> <run>/RESULTS.md and docs/RUNS.md

The run folder is data/runs/<START_DATE>_<END_DATE>/engine-v<ENGINE_VERSION>[-<RUN_LABEL>].
At start a status table shows every step; a step whose outputs exist is skipped, so a run
with everything in place ends after the table. Outputs of steps 3-7 are never overwritten.

Usage (from repo root):
    python -u pipeline/pipeline_bkg.py [--jobs 4] [--dry-run]
    nohup python -u pipeline/pipeline_bkg.py > logs/pipeline.out 2>&1 &
Settings: the USER SETTINGS block below; DEEPGRB_* environment variables take priority
(list in utils/run_options.py). The log is also written to logs/.
"""

# ================================ USER SETTINGS ================================
START_DATE = "2019-03-01"   # first UTC day, included
END_DATE = "2019-06-30"     # last UTC day, included
RUN_LABEL = None            # e.g. "seed1": separate run folder and model bundle (None = default run)
TRAIN_SEED = None           # integer seed; required with FORCE_TRAIN
FORCE_TRAIN = False         # train a new network (needs RUN_LABEL and TRAIN_SEED; hours on GPU)
REUSE_BUNDLE = False        # load an existing labelled bundle instead of stopping
ALLOW_TRAINING = False      # train when no bundle exists for a new period
SKIP_DOWNLOAD = False       # skip steps 1-2 (all daily tables must exist)
SKIP_LOCALIZATION = False   # skip step 6 (localization + classification)
JOBS = 4                    # parallel jobs of steps 2 and 6
# ===============================================================================

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

import pandas as pd

from connections.utils.config import (DATA_DIR, ENERGY_RANGES_KEV, ENGINE_VERSION, FOCUS_MU_MIN, FOCUS_T_MAX_BINS,
                                      FOLD_BKG, FOLD_CSPEC_POS, FOLD_NN, FOLD_POSHIST, GBM_TRIG_DB, LOGS_DIR, NN_PARAMS,
                                      PRED_TRIG_COMPATIBLE_SINCE, SAA_EXCLUSION_BINS, TRIGGER_THRESHOLD_SIGMA,
                                      engine_parameters, run_dir)
from utils.logs import detail, format_duration, header, log, setup_logging, step, summary
from utils.period import window_days
from utils.run_options import (RunOptions, RunOptionsError, bundle_checksum, bundle_seed, manifest_model,
                               parameter_mismatches, read_manifest, resolve_run_options, settings_to_env)

USER_SETTINGS = {"START_DATE": START_DATE, "END_DATE": END_DATE, "RUN_LABEL": RUN_LABEL, "TRAIN_SEED": TRAIN_SEED,
                 "FORCE_TRAIN": FORCE_TRAIN, "REUSE_BUNDLE": REUSE_BUNDLE, "ALLOW_TRAINING": ALLOW_TRAINING,
                 "SKIP_DOWNLOAD": SKIP_DOWNLOAD, "SKIP_LOCALIZATION": SKIP_LOCALIZATION, "JOBS": JOBS}
N_STEPS = 9
CSPEC_DIR, POSHIST_DIR, BKG_DIR = DATA_DIR / FOLD_CSPEC_POS, DATA_DIR / FOLD_POSHIST, DATA_DIR / FOLD_BKG


class PipelineStop(RuntimeError):
    """The run cannot continue safely; the message says why and what to do."""


def rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def newer(target: Path, *sources: Path) -> bool:
    """target exists and is not older than any existing source."""
    if not target.exists():
        return False
    t = target.stat().st_mtime
    return all(t >= s.stat().st_mtime for s in sources if s.exists())


def git_state() -> tuple:
    """(commit, engine code dirty) of the working tree."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", "models", "pipeline", "connections", "utils", "benchmark"],
                                    cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip())
    except OSError:
        commit, dirty = "unknown", True
    return commit, dirty


@dataclass
class Status:
    number: int
    title: str
    done: bool
    output: str
    note: str = ""


class Pipeline:
    def __init__(self, env: dict, opts: RunOptions, jobs: int):
        self.env, self.opts, self.jobs = env, opts, jobs
        self.start, self.end = opts.start_date, opts.end_date
        self.days = window_days(self.start, self.end)
        self.skip_download = env["DEEPGRB_SKIP_DOWNLOAD"] == "1"
        self.skip_localization = env["DEEPGRB_SKIP_LOCALIZATION"] == "1"
        self.run = opts.run_dir
        self.pred_frg, self.pred_bkg = self.run / "pred" / "frg.csv", self.run / "pred" / "bkg.csv"
        self.trig, self.offset = self.run / "trig" / "trig.csv", self.run / "trig" / "offset.csv"
        self.results = self.run / "results"
        self.events = self.results / "events_table.csv"
        self.loc = self.results / "events_table_loc.csv"
        self.classified = self.results / "events_classified.csv"
        self.flags = self.results / "events_flags.csv"
        self.validation = self.run / "validation" / "summary.json"
        self.report = self.run / "RESULTS.md"
        self.executed: List[int] = []
        self._missing_raw: Optional[List[str]] = None

    # ------------------------------------------------------------------ status
    def missing_raw(self) -> List[str]:
        if self._missing_raw is None:
            from models.download_bkg import missing_raw_days
            self._missing_raw = missing_raw_days(self.days, CSPEC_DIR, POSHIST_DIR)
        return self._missing_raw

    def missing_tables(self) -> List[str]:
        return [d for d in self.days if not (BKG_DIR / f"{d}.csv").exists()]

    def status(self) -> List[Status]:
        n = len(self.days)
        tables_missing = len(self.missing_tables())
        if self.skip_download:
            raw = Status(1, "download CSPEC + POSHIST", True, rel(CSPEC_DIR), "skipped (SKIP_DOWNLOAD)")
        else:
            m = len(self.missing_raw())
            raw = Status(1, "download CSPEC + POSHIST", m == 0, f"{rel(CSPEC_DIR)}, {rel(POSHIST_DIR)}", f"{n - m}/{n} days")
        val_inputs = (self.events, self.flags, self.classified)
        return [
            raw,
            Status(2, "preprocess daily tables", tables_missing == 0, rel(BKG_DIR), f"{n - tables_missing}/{n} days"),
            Status(3, "neural background", self.pred_frg.exists() and self.pred_bkg.exists(), rel(self.pred_frg.parent),
                   "symlink to " + rel(self.pred_frg.parent.resolve().parent) if self.pred_frg.parent.is_symlink() else ""),
            Status(4, "Poisson-FOCuS", self.trig.exists() and self.offset.exists(), rel(self.trig.parent),
                   "symlink to " + rel(self.trig.parent.resolve().parent) if self.trig.parent.is_symlink() else ""),
            Status(5, "triggers and events", self.events.exists(), rel(self.events)),
            Status(6, "localization + classification", self.classified.exists() or self.skip_localization, rel(self.classified),
                   "skipped (SKIP_LOCALIZATION)" if self.skip_localization and not self.classified.exists()
                   else ("localized only" if self.loc.exists() and not self.classified.exists() else "")),
            Status(7, "post-processing flags", self.flags.exists(), rel(self.flags)),
            Status(8, "validation", newer(self.validation, *val_inputs), rel(self.validation.parent),
                   "outdated" if self.validation.exists() and not newer(self.validation, *val_inputs) else ""),
            Status(9, "report", newer(self.report, self.validation, self.classified), rel(self.report),
                   "outdated" if self.report.exists() and not newer(self.report, self.validation, self.classified) else ""),
        ]

    def show_status(self, status: List[Status]) -> None:
        log.info("")
        log.info("Status of the run (✔ = output present, step skipped):")
        for s in status:
            log.info(f"  {'✔' if s.done else '✘'} {s.number} {s.title:<32} {s.output}" + (f"  [{s.note}]" if s.note else ""))

    # ------------------------------------------------------------------ manifest
    def model_entry(self) -> dict:
        """The model that produces (or produced) this run's predictions, with seed and checksum."""
        o = self.opts
        if o.mode == "reuse_pred":
            bundle = manifest_model(read_manifest(o.reuse_source)).get("bundle")
        elif o.mode == "resume":
            bundle = manifest_model(read_manifest(self.run)).get("bundle")
        else:
            bundle = rel(o.bundle_dir)
        path = REPO_ROOT / bundle if bundle else None
        return {"bundle": bundle, "mode": o.mode, "seed": bundle_seed(path) if path else None,
                "checksum": bundle_checksum(path) if path else None}

    def check_manifest(self) -> None:
        """Stops when an existing run was produced with other parameters or another model."""
        man = read_manifest(self.run)
        if not man:
            return
        diff = parameter_mismatches(man.get("parameters", {}), engine_parameters(self.start, self.end))
        if diff:
            raise PipelineStop("The run folder was produced with different parameters: "
                               + "; ".join(f"{k}: recorded {a}, now {b}" for k, (a, b) in diff.items())
                               + ". Use another RUN_LABEL or move the folder to data/_archive_<date>/.")
        recorded = manifest_model(man)
        if recorded.get("checksum") and recorded.get("bundle"):
            now = bundle_checksum(REPO_ROOT / recorded["bundle"])
            if now != recorded["checksum"]:
                raise PipelineStop(f"Model bundle {recorded['bundle']} changed since the run was produced "
                                   f"(sha256 {recorded['checksum'][:12]}... recorded, {str(now)[:12]}... now).")
            detail(f"manifest coherent: engine v{man['parameters'].get('engine_version')}, period, parameters, "
                   f"bundle checksum {now[:12]}...")
        else:
            detail(f"manifest coherent: engine v{man.get('parameters', {}).get('engine_version')}, period, parameters "
                   "(bundle checksum not recorded yet)")

    def write_manifest(self, steps: List[int]) -> None:
        """
        New run: records the parameters once. Existing run: parameters are never rewritten; the model
        entry is added if missing and one history line is appended for the steps executed now.
        """
        path = self.run / "manifest.json"
        man = read_manifest(self.run)
        if not man:
            if self.opts.is_labelled:
                self.run.mkdir(parents=True, exist_ok=False)  # a new labelled run never reuses a folder
            self.run.mkdir(parents=True, exist_ok=True)
            man = {"parameters": engine_parameters(self.start, self.end), "run_label": self.opts.label}
        if "model" not in man:
            man["model"] = self.model_entry()
        commit, dirty = git_state()
        versions = {"python": platform.python_version(), "pandas": pd.__version__}
        if "tensorflow" in sys.modules:
            versions["tensorflow"] = sys.modules["tensorflow"].__version__
        man.setdefault("runs", []).append({"started": pd.Timestamp.now(tz="UTC").isoformat(), "git_commit": commit,
                                           "code_dirty": dirty, "steps": steps, "versions": versions})
        path.write_text(json.dumps(man, indent=2))
        if dirty:
            log.warning("Code has uncommitted changes: results are not tied to a commit.")

    def update_manifest(self, key: str, value) -> None:
        path = self.run / "manifest.json"
        man = read_manifest(self.run)
        man[key] = value
        path.write_text(json.dumps(man, indent=2))

    def record_predicted_zero(self, how: str) -> None:
        """Counts predicted background <= 0 (invalid for FOCuS and S) and stores it in the manifest."""
        from models.model_nn import count_nonpositive_predictions
        counts = count_nonpositive_predictions(self.pred_bkg)
        counts["source"] = how
        self.update_manifest("predicted_zero_cells", counts)
        detail(f"predicted background <= 0: {counts['cells']} cells, {counts['bins_any_channel']} bins ({how})")

    # ------------------------------------------------------------------ steps
    def step_download(self) -> None:
        from models.download_bkg import download_days
        df = download_days(self.start, self.end, cspec_dir=CSPEC_DIR, poshist_dir=POSHIST_DIR)
        self._missing_raw = None
        detail(f"raw data complete for {int(df['complete'].sum())}/{len(df)} days")

    def step_preprocess(self) -> None:
        from models.download_bkg import build_day_schedule
        from models.preprocess import build_table
        todo = build_day_schedule(self.start, self.end)
        todo = todo[todo["day"].isin(self.missing_tables()) & ~todo["day"].isin(self.missing_raw())]
        if todo.empty:
            raise PipelineStop("No complete raw day to preprocess: run step 1 (download) first.")
        detail(f"preprocessing {len(todo)} day(s): {', '.join(todo['day'])}")
        build_table(todo, ENERGY_RANGES_KEV, bool_overwrite=False, bool_parallel=True, n_jobs=self.jobs)

    def step_background(self) -> None:
        o = self.opts
        if o.mode == "reuse_pred":
            src = o.reuse_source
            for sub in ("pred", "trig"):
                if not (self.run / sub).exists():
                    (self.run / sub).symlink_to(src / sub, target_is_directory=True)
            src_man = read_manifest(src)
            self.update_manifest("reused_from", {
                "run": rel(src), "engine_version": PRED_TRIG_COMPATIBLE_SINCE, "how": "symlink",
                "steps": ["3 pred/", "4 trig/"], "model_bundle": manifest_model(src_man).get("bundle"),
                "source_git_commit": (src_man.get("runs") or [{}])[0].get("git_commit"),
            })
            detail(f"reusing pred/ and trig/ of {rel(src)} (symlinks): steps 3-4 unchanged since engine v{PRED_TRIG_COMPATIBLE_SINCE}")
            self.record_predicted_zero(f"reused from {src.name}")
            return
        if self.pred_frg.exists() or self.pred_bkg.exists():
            raise PipelineStop(f"Incomplete step 3 outputs in {rel(self.pred_frg.parent)}: move them to an archive and rerun.")
        self.report_devices()
        from models.model_nn import ModelNN
        from utils.run_options import obtain_model
        nn = ModelNN(self.start, self.end, bkg_dir=BKG_DIR, trig_catalog_path=GBM_TRIG_DB)
        nn.prepare(bool_del_trig=True)
        detail(f"model mode: {o.mode} -> {rel(o.bundle_dir)}")
        commit, dirty = git_state()
        obtain_model(nn, o, NN_PARAMS, extra_metadata={
            "git_commit": commit, "code_dirty": dirty, "run_label": o.label, "run_dir": rel(self.run),
            "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
        })
        self.update_manifest("model", self.model_entry())  # bundle now exists: seed and checksum
        nn.predict(self.pred_frg, self.pred_bkg, time_to_del=SAA_EXCLUSION_BINS)
        self.record_predicted_zero("predicted in this run")

    def report_devices(self) -> None:
        """GPUs seen by TensorFlow, or a warning that training would run on CPU."""
        import tensorflow as tf
        gpus = tf.config.list_physical_devices("GPU")
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                log.warning(f"Could not enable memory growth on {gpu.name}: {e}")
        if gpus:
            detail(f"GPU detected: {', '.join(g.name for g in gpus)}")
        else:
            log.warning("No GPU detected by TensorFlow: "
                        + ("TRAINING WILL RUN ON CPU (much slower)." if self.opts.mode == "train" else "inference runs on CPU."))

    def step_focus(self) -> None:
        import numpy as np
        from models.trigger import run_trigger
        from models.trigs.focus import build_focus_runner
        focus = run_trigger(self.pred_frg, self.pred_bkg, self.trig, self.offset,
                            build_focus_runner(mu_min=FOCUS_MU_MIN, t_max=FOCUS_T_MAX_BINS))
        detail(f"max significance {np.nanmax(focus.to_numpy()):.2f} sigma; bins with r1 > {TRIGGER_THRESHOLD_SIGMA} sigma "
               f"on some detector: {int((focus.filter(like='_r1') > TRIGGER_THRESHOLD_SIGMA).any(axis=1).sum())}")

    def step_events(self) -> None:
        from models.analyze import EventAnalyzer
        analyzer = EventAnalyzer(self.pred_frg, self.pred_bkg, self.trig, self.offset, GBM_TRIG_DB)
        _, events = analyzer.run(TRIGGER_THRESHOLD_SIGMA, self.results)
        detail(f"events: {len(events)}; CE tiers: {events['CE'].value_counts().to_dict()}")

    def step_classification(self) -> None:
        from models.event_classifier import classify_events
        if not self.loc.exists():
            from models.localize_event import localize
            detail(f"localizing the events with {self.jobs} job(s) (PSO; slow)")
            localize(self.events, self.pred_frg, self.pred_bkg, BKG_DIR, POSHIST_DIR, self.loc, n_jobs=self.jobs)
        else:
            detail(f"localization already in {rel(self.loc)}")
        ev = classify_events(self.loc, self.classified)
        detail("predicted classes: " + ", ".join(f"{k} {n}" for k, n in ev["predicted_class"].value_counts().items()))

    def step_flags(self) -> None:
        from models.flags import FLAG_COLUMNS, flag_events
        if self.flags.exists():
            raise PipelineStop(f"{rel(self.flags)} exists: refusing to overwrite.")
        f = flag_events(self.run, POSHIST_DIR, self.start, self.end)
        f.to_csv(self.flags, index=False)
        detail("flagged events: " + ", ".join(f"{c} {int(f[c].sum())}" for c in FLAG_COLUMNS))

    def step_validation(self) -> None:
        from benchmark.validate import validate_run
        s = validate_run(self.run, POSHIST_DIR)
        detail(f"GBM catalog: {s['gbm']['detected']}/{s['gbm']['available']} triggers detected"
               + (f"; Crupi known {s['crupi']['known']['matched']}/{s['crupi']['known']['in_window']}, "
                  f"unknown {s['crupi']['unknown']['matched']}/{s['crupi']['unknown']['in_window']}" if s["crupi"]
                  else "; Crupi's tables do not cover this period"))

    def step_report(self) -> None:
        from benchmark.report import write_results, write_runs_index
        detail(f"written {rel(write_results(self.run))} and {rel(write_runs_index())}")

    # ------------------------------------------------------------------ run
    def steps(self) -> List[Callable]:
        return [self.step_download, self.step_preprocess, self.step_background, self.step_focus, self.step_events,
                self.step_classification, self.step_flags, self.step_validation, self.step_report]

    def final_summary(self, t0: float) -> None:
        rows = [f"run folder      : {rel(self.run)}"]
        if self.events.exists():
            ev = pd.read_csv(self.events)
            rows.append(f"events          : {len(ev)} (R {int((ev['CE'] == 'R').sum())}, S {int((ev['CE'] == 'S').sum())}, "
                        f"P {int((ev['CE'] == 'P').sum())})")
        if self.validation.exists():
            s = json.loads(self.validation.read_text())
            rows.append(f"GBM catalog     : {s['gbm']['detected']}/{s['gbm']['available']} triggers, "
                        f"GRB {s['gbm']['grb_detected']}/{s['gbm']['grb_available']}")
            if s["crupi"]:
                c = s["crupi"]
                rows.append(f"Crupi et al.    : known {c['known']['matched']}/{c['known']['in_window']}, "
                            f"unknown {c['unknown']['matched']}/{c['unknown']['in_window']}")
            rows.append(f"no counterpart  : {s['events']['without_counterpart']}")
        rows.append(f"report          : {rel(self.report) if self.report.exists() else 'not written'}")
        rows.append(f"steps executed  : {', '.join(map(str, self.executed)) or 'none (all outputs present)'}")
        rows.append(f"total time      : {format_duration(time.time() - t0)}")
        summary("SUMMARY", rows)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jobs", type=int, help="parallel jobs of steps 2 and 6 (overrides JOBS / DEEPGRB_JOBS)")
    p.add_argument("--dry-run", action="store_true", help="show settings, status and the steps to run; write nothing")
    return p.parse_args(argv)


def main(argv=None) -> int:
    t0 = time.time()
    args = parse_args(argv)
    try:
        env = settings_to_env(USER_SETTINGS, os.environ)
    except RunOptionsError as e:
        setup_logging()
        log.error(f"[settings] {e}")
        return 2
    start, end, label = env["DEEPGRB_START_DATE"], env["DEEPGRB_END_DATE"], env["DEEPGRB_RUN_LABEL"] or None
    jobs = args.jobs or int(env["DEEPGRB_JOBS"] or 1)
    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    log_file = None if args.dry_run else LOGS_DIR / f"pipeline_{start}_{end}{'_' + label if label else ''}_{stamp}.log"
    setup_logging(log_file)

    try:
        window_days(start, end)
        reuse = run_dir(start, end, PRED_TRIG_COMPATIBLE_SINCE) if PRED_TRIG_COMPATIBLE_SINCE != ENGINE_VERSION else None
        opts = resolve_run_options(env, start, end, run_dir(start, end), DATA_DIR / FOLD_NN, reuse_source_dir=reuse)
    except (RunOptionsError, ValueError) as e:
        log.error(f"[run options] {e}")
        return 2

    header([f"DEEPGRB PIPELINE  {start} -> {end}  ({len(window_days(start, end))} days, engine v{ENGINE_VERSION})",
            f"run folder : {rel(opts.run_dir)}",
            f"model      : {opts.mode}  {rel(opts.bundle_dir)}" + (f"  (from {rel(opts.reuse_source)})" if opts.reuse_source else ""),
            f"label {opts.label}, train seed {opts.seed if opts.mode == 'train' else '-'}, jobs {jobs}"
            + (", DRY RUN" if args.dry_run else ""),
            f"log        : {rel(log_file) if log_file else '-'}"])
    pipe = Pipeline(env, opts, jobs)
    try:
        pipe.check_manifest()
        status = pipe.status()
        pipe.show_status(status)
        todo = [s.number for s in status if not s.done]
        if pipe.skip_download and pipe.missing_tables():
            missing = pipe.missing_tables()
            raise PipelineStop(f"SKIP_DOWNLOAD is set but {len(missing)} daily table(s) are missing "
                               f"({', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}).")
        if not todo:
            log.info("")
            log.info("All steps are complete and coherent with the manifest: nothing to do.")
            pipe.final_summary(t0)
            return 0
        log.info("")
        log.info(f"Steps to run: {', '.join(map(str, todo))}")
        if args.dry_run:
            log.info("Dry run: nothing executed, nothing written.")
            return 0
        if 3 in todo and opts.mode == "train":
            log.warning(f"Step 3 will TRAIN a new network (seed {opts.seed}) into {rel(opts.bundle_dir)}.")
        pipe.write_manifest(todo)
        steps = pipe.steps()
        for number in range(1, N_STEPS + 1):
            s = pipe.status()[number - 1]  # re-evaluated: earlier steps may have outdated this one
            if s.done:
                continue
            with step(number, N_STEPS, s.title.capitalize()):
                steps[number - 1]()
            pipe.executed.append(number)
    except (PipelineStop, RunOptionsError, FileExistsError) as e:
        log.error(f"STOP: {e}")
        return 1
    log.info("")
    pipe.final_summary(t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
