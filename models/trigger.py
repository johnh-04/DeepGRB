"""
Multi-core trigger execution engine.
Applies the Poisson-FOCuS sequential change-point algorithm concurrently across all 36 detector-energy channels.
"""

import logging
import os
from pathlib import Path
from typing import Callable, Optional, Tuple
from joblib import Parallel, delayed
import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_PRED, FOLD_TRIG
from utils.keys import get_keys

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def _get_available_cpus() -> int:
    """Detects allocated CPU cores respecting Slurm and cgroup affinity constraints."""
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        return os.cpu_count() or 1


def _process_single_key(
    key: str,
    fermi_series: pd.Series,
    pred_series: pd.Series,
    trigger_func: Callable,
) -> Tuple[str, list, list]:
    """Worker task scanning a single detector-energy channel with Poisson-FOCuS."""
    logging.info(f"Poisson-FOCuS processing channel: {key}")
    out, out_offset = trigger_func(fermi_series, pred_series)
    return key, out, out_offset


def run_trigger(
    start_month: str,
    end_month: str,
    trigger_func: Callable,
    n_jobs: Optional[int] = None,
) -> pd.DataFrame:
    """
    Executes Poisson-FOCuS trigger detection over observed and predicted background series.

    :param start_month: Start month format 'MM-YYYY'
    :param end_month: End month format 'MM-YYYY'
    :param trigger_func: Configured trigger runner (e.g. from models.trigs.focus)
    :param n_jobs: Number of CPU workers (hard-capped to 4 to prevent HPC node memory exhaustion)
    :return: DataFrame containing significance scores per channel
    """
    # Safe multi-core allocation policy on ReCaS HPC nodes
    MAX_WORKERS = 4
    detected_cpus = _get_available_cpus()
    num_workers = min(n_jobs or detected_cpus, MAX_WORKERS)
    logging.info(f"Available CPUs: {detected_cpus}. Operating with SAFE_MAX_WORKERS = {num_workers}")

    pred_dir = DATA_DIR / FOLD_PRED
    frg_file = pred_dir / f"frg_{start_month}_{end_month}.csv"
    bkg_file = pred_dir / f"bkg_{start_month}_{end_month}.csv"

    fermi_data = pd.read_csv(frg_file)
    nn_pred = pd.read_csv(bkg_file)

    # Sanitize zero values to prevent log-likelihood divergences in Poisson-FOCuS
    zero_mask = (fermi_data == 0).any(axis=1) | (nn_pred == 0).any(axis=1)
    if zero_mask.any():
        logging.warning("Excising zero-count observations (assigned to NaN) to preserve statistical validity.")
        fermi_data.loc[zero_mask, nn_pred.columns] = None
        nn_pred.loc[zero_mask, nn_pred.columns] = None

    keys = get_keys()
    dct_res = {}
    dct_offset = {}

    if num_workers > 1:
        results = Parallel(n_jobs=num_workers, backend="loky")(
            delayed(_process_single_key)(k, fermi_data[k].values, nn_pred[k].values, trigger_func)
            for k in keys
        )
        for k, out, out_offset in results:
            dct_res[k] = out
            dct_offset[k] = out_offset
    else:
        for k in keys:
            _, out, out_offset = _process_single_key(k, fermi_data[k].values, nn_pred[k].values, trigger_func)
            dct_res[k] = out
            dct_offset[k] = out_offset

    focus_res = pd.DataFrame(dct_res)
    focus_offset = pd.DataFrame(dct_offset)

    trig_dir = DATA_DIR / FOLD_TRIG
    trig_dir.mkdir(parents=True, exist_ok=True)

    trig_path = trig_dir / f"trig_{start_month}_{end_month}.csv"
    offset_path = trig_dir / f"offset_{start_month}_{end_month}.csv"

    # Save significance tables
    focus_res.to_csv(trig_path, index=False)
    focus_offset.to_csv(offset_path, index=False)
    logging.info(f"Trigger tables saved to: {trig_path} and {offset_path}")

    return focus_res