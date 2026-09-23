import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from joblib import Parallel, delayed
from connections.utils.config import PATH_TO_SAVE, FOLD_PRED, FOLD_TRIG
from utils.keys import get_keys


def _get_available_cpus():
    """
    Determine the actual number of CPU cores available for the current process,
    respecting OS affinity and cgroup allocations on HPC clusters (e.g. Slurm).
    """
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        return os.cpu_count() or 1


def _process_single_key(key, fermi_series, pred_series, trigger):
    """
    Worker function executed per detector-energy combination.
    """
    print(f"Focus trigger... Elaborating key: {key}")
    out, out_offset = trigger(fermi_series, pred_series)
    return key, out, out_offset


def run_trigger(start_month, end_month, trigger, n_jobs=None):
    """
    Manages trigger algorithms and stores results.
    Dynamically adapts execution to the available CPU cores.

    :param start_month: string, format mm-yyyy
    :param end_month: string, format mm-yyyy
    :param trigger: callable trigger algorithm function
    :param n_jobs: int or None. If None, automatically detects allocated cores (1..N).
    :return: pandas DataFrame containing trigger detections
    """
    # Detect available CPU resources
    available_cpus = _get_available_cpus()
    
    # HARD CAP: never use more than 4 workers to protect system memory
    MAX_WORKERS = 4
    
    if n_jobs is None or n_jobs < 1:
        num_workers = min(available_cpus, MAX_WORKERS)
    else:
        num_workers = min(n_jobs, MAX_WORKERS)

    print(f"Detected {available_cpus} raw CPU core(s). Safe limit applied: using {num_workers} worker(s).")

    # Load dataset of foreground and background
    pred_path = os.path.join(PATH_TO_SAVE, FOLD_PRED)
    fermi_data = pd.read_csv(os.path.join(pred_path, f"frg_{start_month}_{end_month}.csv"))
    nn_pred = pd.read_csv(os.path.join(pred_path, f"bkg_{start_month}_{end_month}.csv"))

    # Clean zeros in the datasets
    index_zeros = (fermi_data == 0).any(axis=1) | (nn_pred == 0).any(axis=1)
    if index_zeros.sum() > 0:
        print("Warning: zero counts found in foreground or background. Setting values to None.")
        fermi_data.loc[index_zeros, nn_pred.columns] = None
        nn_pred.loc[index_zeros, nn_pred.columns] = None

    # Retrieve detector/energy channel keys
    keys = get_keys()

    print("Running trigger algorithm...")
    dct_res = {}
    dct_offset = {}

    if num_workers > 1:
        # Multi-core parallel execution
        results = Parallel(n_jobs=num_workers, backend="loky")(
            delayed(_process_single_key)(key, fermi_data[key].values, nn_pred[key].values, trigger)
            for key in keys
        )
        for key, out, out_offset in results:
            dct_res[key] = out
            dct_offset[key] = out_offset
    else:
        # Single-core sequential execution
        for key in keys:
            k, out, out_offset = _process_single_key(key, fermi_data[key].values, nn_pred[key].values, trigger)
            dct_res[k] = out
            dct_offset[k] = out_offset

    focus_res = pd.DataFrame(dct_res)
    focus_offset = pd.DataFrame(dct_offset)

    trig_dir = os.path.join(PATH_TO_SAVE, FOLD_TRIG)
    os.makedirs(trig_dir, exist_ok=True)

    # Save output tables
    trig_file = os.path.join(trig_dir, f"trig_{start_month}_{end_month}.csv")
    offset_file = os.path.join(trig_dir, f"offset_{start_month}_{end_month}.csv")

    focus_res.to_csv(trig_file, index=False, float_format='%.2f')
    focus_offset.to_csv(offset_file, index=False, float_format='%.2f')
    
    print("Done. Trigger detection finished.")
    return focus_res