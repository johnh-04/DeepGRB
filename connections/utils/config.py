"""
Single configuration of DeepGRB: folders, engine version and scientific parameters.

The analysis period is NOT defined here: it is set in the USER SETTINGS block of
pipeline/pipeline_bkg.py (or by DEEPGRB_START_DATE / DEEPGRB_END_DATE), and every other
tool reads it from the manifest.json of the run it works on.

Scientific parameters follow the upstream code that produced Crupi et al. (2023); the three
places where the code differs from the paper text are documented in docs/WORKING_RULES.md §2.
"""

import json
from pathlib import Path
from typing import Optional, Tuple

# ----------------------------------------------------------------------------- folders
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"
LOGS_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
REFERENCE_DIR = BASE_DIR / "benchmark" / "reference"

# subfolders of data/ shared by all periods
FOLD_CSPEC_POS = "cspec"
FOLD_POSHIST = "poshist"
FOLD_BKG = "bkg"
FOLD_NN = "nn_model"

# catalogs (rebuilt from HEASARC by connections/fermi_data_tools.py)
GBM_TRIG_DB = DATA_DIR / "gbm_trig_catalog.csv"
GBM_BURST_DB = DATA_DIR / "gbm_burst_catalog.db"

# ----------------------------------------------------------------------------- engine version
# Outputs of steps 3-5 live in RUNS_DIR/<start>_<end>/engine-v<ENGINE_VERSION>[-<label>]/.
# Bump ENGINE_VERSION whenever a change alters predictions, triggers or events, so a new
# run never reuses results produced by older code.
ENGINE_VERSION = "3"

# ----------------------------------------------------------------------------- scientific parameters
BIN_LENGTH_S = 4.096                      # CSPEC time bin
ENERGY_RANGES_KEV = {"n": [(28, 50), (50, 300), (300, 500)], "b": [(756, 5025), (5025, 50000)]}

# background network (upstream recipe; one network per period)
NN_PARAMS = {"loss_type": "mean", "units": 2048, "epochs": 64, "lr": 0.0008, "bs": 2048, "dropout_rate": 0.02}
SAA_GAP_S = 500.0                         # a data gap longer than this is an SAA passage
SAA_EXCLUSION_BINS = 150                  # upstream: 150 bins (~614 s) masked on each side of such a gap

# Poisson-FOCuS (input: rates in counts/s, as upstream)
FOCUS_MU_MIN = 1.2
FOCUS_T_MAX_BINS = 50                     # 204.8 s, as upstream

# triggers and events
TRIGGER_THRESHOLD_SIGMA = 3.0             # in range r1
MIN_DET_NUMBER = 1
MAX_DET_NUMBER = 13                       # exclusive upper bound; with 12 NaI it never vetoes
MERGE_S = 600                             # triggers closer than this are merged into one event

# post-processing flags (models/flags.py; docs/ORBIT_ANALYSIS.md)
FLAG_EDGE_WINDOW_S = 200.0
FLAG_REGION_DEG = 3.5
FLAG_REGION_GRID_DEG = 0.1
FLAG_ZERO_PAD_BINS = 5

# validation (benchmark/)
MATCH_MARGIN_S = 2 * BIN_LENGTH_S         # primary one-to-one matching rule
SENSITIVITY_MARGINS_S = {"primary (2 bins)": MATCH_MARGIN_S, "10 s": 10.0, "60 s": 60.0, "1200 s": 1200.0}
SAA_GUARD_S = 150.0                       # "near SAA" in the catalog statistics (docs/WORKING_RULES.md §6)
CRUPI_REFERENCE_PERIOD = ("2019-03-01", "2019-07-09")  # period covered by Crupi's tables



# ----------------------------------------------------------------------------- run folders
def period_dir(start_date: str, end_date: str) -> Path:
    """Folder of all the runs of one period."""
    return RUNS_DIR / f"{start_date}_{end_date}"


def run_dir(start_date: str, end_date: str, engine_version: str = ENGINE_VERSION, label: Optional[str] = None) -> Path:
    """Output folder of the engine for one period, code version and (optional) run label."""
    name = f"engine-v{engine_version}" + (f"-{label}" if label else "")
    return period_dir(start_date, end_date) / name


def read_manifest(run: Path) -> dict:
    path = Path(run) / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def run_period(run: Path) -> Tuple[str, str]:
    """(start_date, end_date) of a run, from its manifest (fallback: the period folder name)."""
    period = read_manifest(run).get("parameters", {}).get("period")
    if period:
        return period["start_date"], period["end_date"]
    start, _, end = Path(run).resolve().parent.name.partition("_")
    if not (start and end):
        raise ValueError(f"Cannot read the period of run {run}")
    return start, end


def engine_parameters(start_date: str, end_date: str) -> dict:
    """Scientific parameters of the engine, recorded once in manifest.json["parameters"]."""
    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "engine_version": ENGINE_VERSION,
        "bin_length_s": BIN_LENGTH_S,
        "energy_ranges_keV": ENERGY_RANGES_KEV,
        "saa_gap_s": SAA_GAP_S,
        "saa_exclusion_bins_each_side": SAA_EXCLUSION_BINS,
        "focus": {"mu_min": FOCUS_MU_MIN, "t_max_bins": FOCUS_T_MAX_BINS, "input": "rates (counts/s)"},
        "trigger": {"threshold_sigma": TRIGGER_THRESHOLD_SIGMA, "range": "r1", "min_detectors": MIN_DET_NUMBER,
                    "max_detectors_exclusive": MAX_DET_NUMBER},
        "merge_s": MERGE_S,
        "significance": "S=sum(N-B)/sqrt(sum(B)), triggered detectors, offset-extended interval, max over 21 quantile cuts",
        "flags": {"edge_window_s": FLAG_EDGE_WINDOW_S, "region_deg": FLAG_REGION_DEG,
                  "region_grid_deg": FLAG_REGION_GRID_DEG, "zero_pad_bins": FLAG_ZERO_PAD_BINS},
    }
