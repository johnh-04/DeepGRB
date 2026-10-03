"""
MAE and MeAE performance aggregator across various dropout configurations.
Evaluates model summary text files exported during background neural network training.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_NN

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def parse_mae_file(filepath: Path) -> Optional[pd.Series]:
    """
    Parses detector-channel MAE/MeAE values from a training output report file.
    Extracts the channel metrics reliably by inspecting whitespace-separated tokens.
    """
    if not filepath.exists():
        logging.warning(f"Report file not found: {filepath}")
        return None

    try:
        # Standard structure: each line reports metrics for one channel
        # e.g., 'MAE train of n0_r0 : 5.040   MAE test of n0_r0 : 5.800 ...'
        df_raw = pd.read_csv(filepath, sep=r"\s+", header=None, engine="python")
        
        # Identify the numeric column containing test metrics (column 14 in original Crupi format)
        if df_raw.shape[1] >= 15:
            # Drop NaN rows or non-numeric tokens
            val_col = pd.to_numeric(df_raw.iloc[:, 14], errors="coerce").dropna()
            return val_col
        else:
            logging.warning(f"Unexpected column count ({df_raw.shape[1]}) in {filepath}")
            return None
    except Exception as e:
        logging.error(f"Failed parsing {filepath}: {e}")
        return None


def run_statistics(model_logs_dir: Optional[Path] = None) -> Dict[str, Dict[str, float]]:
    """Aggregates and compares performance across dropout rates."""
    target_dir = model_logs_dir or (DATA_DIR / FOLD_NN)
    logging.info(f"Scanning directory for model summary reports: {target_dir}")

    # Standard model configurations evaluated in Crupi et al.
    model_patterns = {
        "Dropout 0.0002": "*do_0002*.txt",
        "Dropout 0.002":  "*do_002*.txt",
        "Dropout 0.02":   "*do_02*.txt",
        "Classic (0.05)": "*classic*.txt",
        "Dropout 0.2":    "*do_2*.txt",
    }

    results: Dict[str, Dict[str, float]] = {}

    for label, pattern in model_patterns.items():
        matched_files = sorted(list(target_dir.glob(pattern)))
        if not matched_files:
            continue

        series = parse_mae_file(matched_files[0])
        if series is not None and not series.empty:
            mean_val = float(series.mean())
            std_val = float(series.std())
            results[label] = {"mean": mean_val, "std": std_val}
            print(f"[{label:16s}] Mean Test MAE: {mean_val:.4f} +/- {std_val:.4f}")

    if not results:
        logging.info("No matching dropout log reports found in directory. Check path or filenames.")

    return results


if __name__ == "__main__":
    run_statistics()