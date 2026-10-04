"""
Run options from environment variables: where a pipeline run writes, which model bundle it
uses and whether it trains. Pure logic (no TensorFlow), so it can be tested directly.

Environment variables
    DEEPGRB_RUN_LABEL      label of a separate run: data/runs/<start>_<end>/engine-v<N>-<label>/
                           and bundle data/nn_model/bundles/model_<start>_<end>_<label>/.
                           The folder must not exist yet (nothing is ever overwritten).
    DEEPGRB_FORCE_TRAIN=1  train a new network even for the legacy 2019 period; the legacy
                           model is never loaded. Requires DEEPGRB_RUN_LABEL and DEEPGRB_TRAIN_SEED.
    DEEPGRB_TRAIN_SEED     integer seed for python/numpy/TensorFlow (default 0 when not forcing).
    DEEPGRB_REUSE_BUNDLE=1 if the labelled bundle already exists, load it instead of failing.
    DEEPGRB_ALLOW_TRAINING=1  allow training when no bundle exists (non-legacy periods).

Without DEEPGRB_RUN_LABEL and DEEPGRB_FORCE_TRAIN the behaviour is the historical one:
default run folder used as a cache, legacy model for 2019-03-01..2019-06-30.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

LEGACY_PERIOD = ("2019-03-01", "2019-06-30")
LEGACY_H5_NAME = "model_03-2019_07-2019_4.4_2026-09-21.h5"
DEFAULT_TRAIN_SEED = 0
_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class RunOptionsError(RuntimeError):
    """Invalid or unsafe combination of run options."""


@dataclass(frozen=True)
class RunOptions:
    start_date: str
    end_date: str
    label: Optional[str]
    run_dir: Path
    bundle_dir: Path
    legacy_h5: Path
    mode: str  # "load_bundle" | "wrap_legacy" | "train" | "unavailable"
    seed: int
    force_train: bool
    reuse_bundle: bool

    @property
    def is_labelled(self) -> bool:
        return self.label is not None


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "") == "1"


def resolve_run_options(env: Mapping[str, str], start_date: str, end_date: str,
                        default_run_dir: Path, nn_dir: Path) -> RunOptions:
    """Decides run folder, bundle and model mode; raises RunOptionsError before anything is written."""
    label = env.get("DEEPGRB_RUN_LABEL") or None
    force = _flag(env, "DEEPGRB_FORCE_TRAIN")
    reuse = _flag(env, "DEEPGRB_REUSE_BUNDLE")
    allow = _flag(env, "DEEPGRB_ALLOW_TRAINING") or force
    seed_env = env.get("DEEPGRB_TRAIN_SEED")

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

    legacy_h5 = nn_dir / LEGACY_H5_NAME
    bundles = nn_dir / "bundles"
    is_legacy_period = (start_date, end_date) == LEGACY_PERIOD

    if label is not None:
        run = default_run_dir.parent / f"{default_run_dir.name}-{label}"
        bundle = bundles / f"model_{start_date}_{end_date}_{label}"
        if run.exists():
            raise RunOptionsError(f"Run folder {run} already exists: move it to an archive or choose another label.")
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
        run = default_run_dir
        bundle = bundles / (legacy_h5.stem if is_legacy_period else f"model_{start_date}_{end_date}_seed{seed}")
        if bundle.exists():
            mode = "load_bundle"
        elif is_legacy_period and legacy_h5.exists():
            mode = "wrap_legacy"
        elif allow:
            mode = "train"
        else:
            # historical behaviour: only an error when step 3 actually needs the model
            mode = "unavailable"

    return RunOptions(start_date, end_date, label, run, bundle, legacy_h5, mode, seed, force, reuse)


def obtain_model(nn, opts: RunOptions, train_params: Mapping, extra_metadata: Optional[Mapping] = None) -> None:
    """Loads, wraps or trains the network of `nn` (a prepared ModelNN) according to opts.mode."""
    if opts.mode == "load_bundle":
        nn.load_bundle(opts.bundle_dir)
    elif opts.mode == "wrap_legacy":
        nn.bundle_from_legacy_h5(opts.legacy_h5, opts.bundle_dir)
    elif opts.mode == "train":
        nn.train(opts.bundle_dir, seed=opts.seed, extra_metadata=dict(extra_metadata or {}), **train_params)
    elif opts.mode == "unavailable":
        raise RunOptionsError(f"No model bundle {opts.bundle_dir.name}: set DEEPGRB_ALLOW_TRAINING=1 to train one.")
    else:
        raise RunOptionsError(f"Unknown model mode {opts.mode!r}")
