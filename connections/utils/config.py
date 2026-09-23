import os
from pathlib import Path

# Absolute path of this file: .../DeepGRB/connections/utils/config.py
CURRENT_FILE = Path(__file__).resolve()

# Traverse up to locate the project root ('DeepGRB')
BASE_DIR = CURRENT_FILE
for parent in [CURRENT_FILE] + list(CURRENT_FILE.parents):
    if parent.name == "DeepGRB":
        BASE_DIR = parent
        break
else:
    # Direct relative fallback: utils -> connections -> DeepGRB
    BASE_DIR = CURRENT_FILE.parent.parent.parent

# Main data directory: .../DeepGRB/data/
DATA_DIR = BASE_DIR / "data"
PATH_TO_SAVE = str(DATA_DIR) + "/"

# Subdirectories inside data/
FOLD_CSPEC_POS = "cspec"
FOLD_BKG = "bkg"
FOLD_PRED = "pred"
FOLD_NN = "nn_model"
FOLD_TRIG = "trig"
FOLD_PLOT = "plots"
FOLD_POSHIST = "poshist"

# Results directory: .../DeepGRB/data/results/
FOLD_RES = str(DATA_DIR / "results") + "/"

# GRB table path
PATH_GRB_TABLE = str(DATA_DIR / "grb_classification" / "df_grb.csv")

# Catalogs and databases resolution with root fallback
GBM_BURST_DB = DATA_DIR / "gbm_burst_catalog.db"
GBM_TRIG_DB = DATA_DIR / "gbm_trig_catalog.csv"
DEEP_GRB_CSV = DATA_DIR / "DeepGRB_catalog.csv"

# If files reside in the root of DeepGRB instead of data/
if not DEEP_GRB_CSV.exists() and (BASE_DIR / "DeepGRB_catalog.csv").exists():
    GBM_BURST_DB = BASE_DIR / "gbm_burst_catalog.db"
    GBM_TRIG_DB = BASE_DIR / "gbm_trig_catalog.csv"
    DEEP_GRB_CSV = BASE_DIR / "DeepGRB_catalog.csv"

db_path = str(CURRENT_FILE.parent)