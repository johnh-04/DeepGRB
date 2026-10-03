import os
from pathlib import Path

# Absolute path of this file: .../DeepGRB/connections/utils/config.py
CURRENT_FILE = Path(__file__).resolve()

# Dynamically locate project root ('DeepGRB')
BASE_DIR = None
for parent in [CURRENT_FILE] + list(CURRENT_FILE.parents):
    if parent.name == "DeepGRB":
        BASE_DIR = parent
        break

if BASE_DIR is None:
    # Direct fallback: utils -> connections -> DeepGRB
    BASE_DIR = CURRENT_FILE.parents[2]

# Analysis window: explicit UTC calendar days, both ends included.
# Shared by download and benchmark (Crupi et al. 2019 period).
START_DATE = "2019-03-01"
END_DATE = "2019-07-09"

# Root directories
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"

# Ensure essential base folders exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Path strings for backward-compatibility with legacy scripts
PATH_TO_SAVE = str(DATA_DIR) + "/"
FOLD_RES = str(RESULTS_DIR) + "/"

# Subdirectory names inside data/
FOLD_CSPEC_POS = "cspec"
FOLD_BKG = "bkg"
FOLD_PRED = "pred"
FOLD_NN = "nn_model"
FOLD_TRIG = "trig"
FOLD_PLOT = "plots"
FOLD_POSHIST = "poshist"

# Target catalogs and tables
PATH_GRB_TABLE = DATA_DIR / "grb_classification" / "df_grb.csv"
PATH_GRB_TABLE.parent.mkdir(parents=True, exist_ok=True)

GBM_BURST_DB = DATA_DIR / "gbm_burst_catalog.db"
GBM_TRIG_DB = DATA_DIR / "gbm_trig_catalog.csv"
DEEP_GRB_CSV = DATA_DIR / "DeepGRB_catalog.csv"

# Fallback check if catalog files reside in the root of DeepGRB
if not DEEP_GRB_CSV.exists() and (BASE_DIR / "DeepGRB_catalog.csv").exists():
    GBM_BURST_DB = BASE_DIR / "gbm_burst_catalog.db"
    GBM_TRIG_DB = BASE_DIR / "gbm_trig_catalog.csv"
    DEEP_GRB_CSV = BASE_DIR / "DeepGRB_catalog.csv"