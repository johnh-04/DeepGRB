"""
Runs the Poisson-FOCuS change-point search on every detector-range channel.

Inputs are the observed (frg) and predicted (bkg) rate matrices written by
ModelNN.predict; they are read only. Missing or non-positive cells reach FOCuS
as NaN background, which resets its change-point curves (SAA edges, gaps).
"""

import logging
import os
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from utils.keys import get_keys

logger = logging.getLogger(__name__)

MAX_WORKERS = 4  # safe on ReCaS nodes (4 vCPU / 16 GB)


def _available_cpus() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        return os.cpu_count() or 1


def focus_inputs(x: pd.Series, b: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """Observed and background arrays for FOCuS; the background is NaN wherever either value is missing or <= 0."""
    x = x.to_numpy(dtype=float)
    b = b.to_numpy(dtype=float).copy()
    invalid = ~np.isfinite(x) | ~np.isfinite(b) | (x <= 0) | (b <= 0)
    b[invalid] = np.nan
    return x, b


def _run_channel(key: str, x: np.ndarray, b: np.ndarray, trigger_func: Callable) -> Tuple[str, list, list]:
    out, out_offset = trigger_func(x, b)
    return key, out, out_offset


def run_trigger(
    frg_path: Path,
    bkg_path: Path,
    trig_path: Path,
    offset_path: Path,
    trigger_func: Callable,
    n_jobs: Optional[int] = None,
) -> pd.DataFrame:
    """
    Computes FOCuS significance and change-point offset for the 36 channels and
    writes them to trig_path / offset_path (new files only).
    """
    trig_path, offset_path = Path(trig_path), Path(offset_path)
    for p in (trig_path, offset_path):
        if p.exists():
            raise FileExistsError(f"Refusing to overwrite {p}")
        p.parent.mkdir(parents=True, exist_ok=True)

    keys = get_keys()
    frg = pd.read_csv(frg_path, usecols=keys)
    bkg = pd.read_csv(bkg_path, usecols=keys)
    if len(frg) != len(bkg):
        raise ValueError(f"frg ({len(frg)}) and bkg ({len(bkg)}) have different lengths")

    inputs = {k: focus_inputs(frg[k], bkg[k]) for k in keys}
    n_invalid = sum(int(np.isnan(b).sum()) for _, b in inputs.values())
    logger.info(f"FOCuS inputs: {len(frg)} bins x {len(keys)} channels, {n_invalid} invalid cells passed as NaN")

    workers = min(n_jobs or _available_cpus(), MAX_WORKERS)
    if workers > 1:
        results = Parallel(n_jobs=workers, backend="loky")(
            delayed(_run_channel)(k, *inputs[k], trigger_func) for k in keys
        )
    else:
        results = [_run_channel(k, *inputs[k], trigger_func) for k in keys]

    focus_res = pd.DataFrame({k: out for k, out, _ in results})[keys]
    focus_offset = pd.DataFrame({k: off for k, _, off in results})[keys]
    focus_res.to_csv(trig_path, index=False)
    focus_offset.to_csv(offset_path, index=False)
    logger.info(f"Wrote {trig_path} and {offset_path}")
    return focus_res
