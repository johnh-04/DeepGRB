"""
Run options and run manifest: where a pipeline run writes, which model bundle it uses, whether
it trains, and what is recorded about it. Pure logic (no TensorFlow), so it can be tested directly.

Settings come from the USER SETTINGS block of pipeline/pipeline_bkg.py; the environment
variables below take priority over it.

    DEEPGRB_START_DATE / DEEPGRB_END_DATE   analysis period, 'YYYY-MM-DD', both days included
    DEEPGRB_RUN_LABEL      label of a separate run: data/runs/<start>_<end>/engine-v<N>-<label>/
                           and bundle data/nn_model/bundles/model_<start>_<end>_<label>/.
    DEEPGRB_FORCE_TRAIN=1  train a new network. Requires DEEPGRB_RUN_LABEL and DEEPGRB_TRAIN_SEED.
    DEEPGRB_TRAIN_SEED     integer seed for python/numpy/TensorFlow (default 0 when not forcing).
    DEEPGRB_REUSE_BUNDLE=1 if the labelled bundle already exists, load it instead of failing.
    DEEPGRB_ALLOW_TRAINING=1  allow training when no bundle exists for the period.
    DEEPGRB_SKIP_DOWNLOAD=1   skip steps 1-2 (every daily table must exist).
    DEEPGRB_SKIP_LOCALIZATION=1  skip step 6 (localization + classification).
    DEEPGRB_JOBS           parallel jobs of step 6.

Safety rules: a new labelled run never reuses an existing folder; an existing run (labelled or
not) only resumes its missing steps and its outputs are never overwritten; training needs
DEEPGRB_FORCE_TRAIN with an explicit seed and a label (or DEEPGRB_ALLOW_TRAINING for new periods).
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

DEFAULT_TRAIN_SEED = 0
_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
PRED_TRIG_FILES = ("pred/frg.csv", "pred/bkg.csv", "trig/trig.csv", "trig/offset.csv")

# USER SETTINGS name -> environment variable
SETTINGS_ENV = {
    "START_DATE": "DEEPGRB_START_DATE",
    "END_DATE": "DEEPGRB_END_DATE",
    "RUN_LABEL": "DEEPGRB_RUN_LABEL",
    "TRAIN_SEED": "DEEPGRB_TRAIN_SEED",
    "FORCE_TRAIN": "DEEPGRB_FORCE_TRAIN",
    "REUSE_BUNDLE": "DEEPGRB_REUSE_BUNDLE",
    "ALLOW_TRAINING": "DEEPGRB_ALLOW_TRAINING",
    "SKIP_DOWNLOAD": "DEEPGRB_SKIP_DOWNLOAD",
    "SKIP_LOCALIZATION": "DEEPGRB_SKIP_LOCALIZATION",
    "JOBS": "DEEPGRB_JOBS",
}


class RunOptionsError(RuntimeError):
    """Invalid or unsafe combination of run options."""


def settings_to_env(settings: Mapping[str, object], environ: Mapping[str, str]) -> Dict[str, str]:
    """
    DEEPGRB_* mapping from the USER SETTINGS block, overridden by the environment.
    Booleans become "1"/"", None becomes "" (unset).
    """
    out = {}
    for name, var in SETTINGS_ENV.items():
        value = settings.get(name)
        if isinstance(value, bool):
            value = "1" if value else ""
        out[var] = "" if value is None else str(value)
        if environ.get(var, "") != "":
            out[var] = environ[var]
    if not out["DEEPGRB_START_DATE"] or not out["DEEPGRB_END_DATE"]:
        raise RunOptionsError("START_DATE and END_DATE must be set (USER SETTINGS or DEEPGRB_START_DATE/DEEPGRB_END_DATE).")
    return out


@dataclass(frozen=True)
class RunOptions:
    start_date: str
    end_date: str
    label: Optional[str]
    run_dir: Path
    bundle_dir: Path
    mode: str  # "load_bundle" | "train" | "unavailable" | "resume"
    seed: int
    force_train: bool
    reuse_bundle: bool

    @property
    def is_labelled(self) -> bool:
        return self.label is not None


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "") == "1"


def has_pred_trig(run: Path) -> bool:
    return all((run / f).exists() for f in PRED_TRIG_FILES)


def resolve_run_options(env: Mapping[str, str], start_date: str, end_date: str,
                        default_run_dir: Path, nn_dir: Path) -> RunOptions:
    """Decides run folder, bundle and model mode; raises RunOptionsError before anything is written."""
    label = env.get("DEEPGRB_RUN_LABEL") or None
    force = _flag(env, "DEEPGRB_FORCE_TRAIN")
    reuse = _flag(env, "DEEPGRB_REUSE_BUNDLE")
    allow = _flag(env, "DEEPGRB_ALLOW_TRAINING") or force
    seed_env = env.get("DEEPGRB_TRAIN_SEED") or None

    if label is not None and not _LABEL_RE.match(label):
        raise RunOptionsError(f"DEEPGRB_RUN_LABEL={label!r}: use only letters, digits, '-' and '_'.")
    if force and label is None:
        raise RunOptionsError("DEEPGRB_FORCE_TRAIN=1 requires DEEPGRB_RUN_LABEL: the default run folder must stay untouched.")
    if force and seed_env is None:
        raise RunOptionsError("DEEPGRB_FORCE_TRAIN=1 requires DEEPGRB_TRAIN_SEED (the seed must be explicit).")
    try:
        seed = int(seed_env) if seed_env is not None else DEFAULT_TRAIN_SEED
    except ValueError:
        raise RunOptionsError(f"DEEPGRB_TRAIN_SEED={seed_env!r} is not an integer.") from None

    bundles = nn_dir / "bundles"
    run = default_run_dir if label is None else default_run_dir.parent / f"{default_run_dir.name}-{label}"

    # an existing run with its predictions only resumes the missing steps (no model needed)
    if run.exists() and has_pred_trig(run):
        if force:
            raise RunOptionsError(f"Run folder {run} already has predictions: DEEPGRB_FORCE_TRAIN would retrain into it. "
                                  "Choose another label.")
        bundle = manifest_model(read_manifest(run)).get("bundle") or "unknown"
        return RunOptions(start_date, end_date, label, run, Path(bundle), "resume", seed, force, reuse)
    if label is not None and run.exists():
        raise RunOptionsError(f"Run folder {run} exists but is incomplete (no pred/ and trig/): "
                              "move it to an archive or choose another label.")

    if label is not None:
        bundle = bundles / f"model_{start_date}_{end_date}_{label}"
        if bundle.exists():
            if not reuse:
                raise RunOptionsError(f"Model bundle {bundle} already exists: set DEEPGRB_REUSE_BUNDLE=1 to use it "
                                      "or choose another label.")
            mode = "load_bundle"
        elif allow:
            mode = "train"
        else:
            raise RunOptionsError(f"No bundle {bundle.name}: set DEEPGRB_FORCE_TRAIN=1 (with DEEPGRB_TRAIN_SEED) to train it.")
    else:
        bundle = bundles / f"model_{start_date}_{end_date}_seed{seed}"
        if bundle.exists():
            mode = "load_bundle"
        elif allow:
            mode = "train"
        else:
            # only an error when step 3 actually needs the model
            mode = "unavailable"

    return RunOptions(start_date, end_date, label, run, bundle, mode, seed, force, reuse)


def obtain_model(nn, opts: RunOptions, train_params: Mapping, extra_metadata: Optional[Mapping] = None) -> None:
    """Loads or trains the network of `nn` (a prepared ModelNN) according to opts.mode."""
    if opts.mode == "load_bundle":
        nn.load_bundle(opts.bundle_dir)
    elif opts.mode == "train":
        nn.train(opts.bundle_dir, seed=opts.seed, extra_metadata=dict(extra_metadata or {}), **train_params)
    elif opts.mode == "resume":
        raise RunOptionsError(f"Run {opts.run_dir.name} already has its predictions: no model is needed.")
    elif opts.mode == "unavailable":
        raise RunOptionsError(f"No model bundle {opts.bundle_dir.name}: set DEEPGRB_ALLOW_TRAINING=1 to train one.")
    else:
        raise RunOptionsError(f"Unknown model mode {opts.mode!r}")


# ----------------------------------------------------------------------------- manifest
def read_manifest(run: Path) -> dict:
    path = Path(run) / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def manifest_model(man: Mapping) -> dict:
    """
    The model that produced a run's predictions: {"bundle", "seed", "checksum", ...}.
    Reads the "model" entry (since the consolidation) or the fields of older manifests.
    """
    if man.get("model"):
        return dict(man["model"])
    reused = man.get("reused_from") or {}
    bundle = reused.get("model_bundle") or man.get("parameters", {}).get("model_bundle")
    return {"bundle": bundle} if bundle else {}


def bundle_checksum(bundle_dir: Path) -> Optional[str]:
    """sha256 over the files of a model bundle (name + content, sorted), None if it does not exist."""
    bundle_dir = Path(bundle_dir)
    if not bundle_dir.is_dir():
        return None
    h = hashlib.sha256()
    for f in sorted(p for p in bundle_dir.iterdir() if p.is_file()):
        h.update(f.name.encode())
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def bundle_seed(bundle_dir: Path) -> Optional[int]:
    """Training seed recorded in the bundle metadata (None if not recorded)."""
    meta = Path(bundle_dir) / "metadata.json"
    return json.loads(meta.read_text()).get("seed") if meta.exists() else None


# keys of "parameters" that must match for a run to be resumed by the current code
COMPARED_PARAMETERS = ("period", "engine_version", "bin_length_s", "energy_ranges_keV", "saa_gap_s",
                       "saa_exclusion_bins_each_side", "focus", "trigger", "merge_s")


def parameter_mismatches(recorded: Mapping, current: Mapping) -> Dict[str, tuple]:
    """{key: (recorded, current)} for the compared parameters that differ (JSON-normalised)."""
    norm = lambda v: json.loads(json.dumps(v))  # noqa: E731 - tuples -> lists
    return {k: (recorded.get(k), current.get(k)) for k in COMPARED_PARAMETERS
            if k in recorded and norm(recorded.get(k)) != norm(current.get(k))}
