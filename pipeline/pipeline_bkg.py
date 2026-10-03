"""
DeepGRB Production Pipeline.
Executes the full chain: Data Ingestion (with auto-retry) -> Preprocessing ->
Neural Background Estimation -> Poisson-FOCuS Triggering -> Clustering ->
Catalog Pre-Matching & Classification -> Event Localization -> Benchmark Evaluation.
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, List

# ----------------------------------------------------------------------
# ROOT PATH RESOLUTION & WORKING DIRECTORY ANCHOR
# ----------------------------------------------------------------------
# Resolve repository root from pipeline/ directory to prevent ModuleNotFoundError
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force working directory to repository root for deterministic relative paths
os.chdir(REPO_ROOT)

import matplotlib
matplotlib.use("Agg")  # Headless mode for cluster execution
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix
import tensorflow as tf

from connections.utils.config import (
    DATA_DIR,
    END_DATE,
    START_DATE,
    FOLD_BKG,
    FOLD_CSPEC_POS,
    FOLD_POSHIST,
    FOLD_NN,
    FOLD_PRED,
    FOLD_TRIG,
    RESULTS_DIR,
    GBM_TRIG_DB,
)
from models.download_bkg import download_days
from models.preprocess import build_table
from models.model_nn import ModelNN
from models.trigger import run_trigger
from models.trigs.focus import build_focus_runner
from models.analyze import analyze
from models.event_classifier import CrupiEventClassifier
from models.localize_event import localize
from models.utils.GBMutils import add_trig_gbm_to_frg
from utils.period import days_with_data, in_window

# Logging setup
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Operational intervals & production parameters
ERANGE = {"n": [(28, 50), (50, 300), (300, 500)], "b": [(756, 5025), (5025, 50000)]}
# Download and benchmark use START_DATE/END_DATE (config, inclusive).
# The month labels below only name the cached NN/trigger/result files.
START_MONTH = "03-2019"
END_MONTH = "07-2019"
TIMEFRAME_LABEL = f"{START_MONTH}_{END_MONTH}"

# Production thresholds
FOCUS_MU_MIN = 1.20
FOCUS_T_MAX = 50
ANALYZE_THRESHOLD = 3.0
MATCH_DELTA_T_SEC = 1200.0  # Bi-directional matching tolerance window

cspec_dir = DATA_DIR / FOLD_CSPEC_POS
poshist_dir = DATA_DIR / FOLD_POSHIST
bkg_dir = DATA_DIR / FOLD_BKG
pred_dir = DATA_DIR / FOLD_PRED
nn_model_dir = DATA_DIR / FOLD_NN
trig_dir = DATA_DIR / FOLD_TRIG
results_dir = RESULTS_DIR

for p in [cspec_dir, poshist_dir, bkg_dir, pred_dir, nn_model_dir, trig_dir, results_dir]:
    p.mkdir(parents=True, exist_ok=True)


def clean_label(label: Any) -> str:
    """Normalizes label strings for reliable classification mapping."""
    if pd.isna(label) or not str(label).strip():
        return "UNKNOWN"
    lbl = str(label).strip().upper()
    if "GRB" in lbl: return "GRB"
    if "SFL" in lbl or "SOLAR" in lbl: return "SF"
    if "TGF" in lbl: return "TGF"
    if "SGR" in lbl: return "SGR"
    if "LOC" in lbl: return "UNC(LP)"
    if "UNC" in lbl: return "UNC"
    return lbl


# ======================================================================
# STEP 1/7: DATA INGESTION WITH RESILIENCE CHECKS
# ======================================================================
def run_step_download() -> pd.DataFrame:
    print(f"\n[STEP 1/7] Data Ingestion & Integrity Check ({START_DATE} to {END_DATE}, inclusive)...")
    # Idempotent: complete days are checked on disk only, missing files are fetched per detector.
    df_days = download_days(START_DATE, END_DATE, cspec_dir=cspec_dir, poshist_dir=poshist_dir)
    n_ok = int(df_days["complete"].sum())
    logging.info(f"Raw data complete for {n_ok}/{len(df_days)} days.")
    return df_days


# ======================================================================
# STEP 2/7: PREPROCESSING (Energy Integration & Tables Generation)
# ======================================================================
def run_step_preprocess(df_days: pd.DataFrame) -> None:
    print(f"\n[STEP 2/7] Preprocessing Module into: {bkg_dir.name}/...")
    # build_table skips days whose table already exists, so only new days are processed.
    todo = df_days[df_days["complete"] & ~df_days["day"].apply(lambda d: (bkg_dir / f"{d}.csv").exists())]
    if todo.empty:
        logging.info("All complete days already have a preprocessed table.")
        return
    logging.info(f"Preprocessing {len(todo)} new day(s): {', '.join(todo['day'])}")
    build_table(todo, ERANGE, bool_overwrite=False, bool_parallel=True, n_jobs=4)


# ======================================================================
# STEP 3/7: NEURAL NETWORK BACKGROUND ESTIMATION
# ======================================================================
def run_step_neural_network() -> None:
    print(f"\n[STEP 3/7] Neural Background Estimation ({TIMEFRAME_LABEL})...")
    frg_path = pred_dir / f"frg_{TIMEFRAME_LABEL}.csv"
    bkg_path = pred_dir / f"bkg_{TIMEFRAME_LABEL}.csv"

    # Hardware check & dynamic memory growth
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        logging.info(f"GPU device detected: {gpus[0].name}")
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                logging.warning(f"Memory growth initialization warning: {e}")
    else:
        logging.warning("No GPU device detected. Running execution on multi-core CPU.")

    if not (frg_path.exists() and bkg_path.exists()):
        nn = ModelNN(START_MONTH, END_MONTH)
        nn.prepare(bool_del_trig=True)

        saved_models = list(nn_model_dir.glob("*.keras")) + list(nn_model_dir.glob("*.h5"))
        train_flag = len(saved_models) == 0

        if not train_flag:
            logging.info(f"Trained model checkpoint found ({saved_models[0].name}). Skipping training.")
        else:
            logging.info("No existing model checkpoint found. Training Neural Network on HPC...")

        nn.train(
            bool_train=train_flag,
            loss_type="mean",
            units=2048,
            epochs=64,
            lr=0.0008,
            bs=8192,
            dropout_rate=0.02,
        )

        logging.info("Generating background predictions across continuous timeline...")
        nn.predict(time_to_del=150)
    else:
        logging.info(f"Using cached neural background estimations from: {frg_path.name}")


# ======================================================================
# STEP 4/7: POISSON-FOCUS TRIGGER DETECTION (Fast Cache Bypass)
# ======================================================================
def run_step_trigger() -> None:
    print(f"\n[STEP 4/7] Poisson-FOCuS Anomaly Detection...")
    trig_csv = trig_dir / f"trig_{TIMEFRAME_LABEL}.csv"
    offset_csv = trig_dir / f"offset_{TIMEFRAME_LABEL}.csv"

    # Fast path: skip expensive disk I/O, sanitization, and execution if caches exist
    if trig_csv.exists() and offset_csv.exists() and trig_csv.stat().st_size > 0:
        logging.info(
            f"Found existing Poisson-FOCuS triggers at {trig_csv.name}. "
            f"Skipping sanitization, catalog synchronization, and detection execution."
        )
        return

    frg_path = pred_dir / f"frg_{TIMEFRAME_LABEL}.csv"
    bkg_path = pred_dir / f"bkg_{TIMEFRAME_LABEL}.csv"

    logging.info("Sanitizing zero and NaN counts in BKG/FRG matrices...")
    df_frg = pd.read_csv(frg_path)
    df_bkg = pd.read_csv(bkg_path)
    data_cols = [c for c in df_bkg.columns if c.startswith(("n", "b"))]

    # Fill missing values and enforce strictly positive rates for Poisson statistics
    df_frg[data_cols] = df_frg[data_cols].fillna(10.0)
    df_bkg[data_cols] = df_bkg[data_cols].fillna(10.0)
    for col in data_cols:
        df_frg.loc[df_frg[col] <= 0.0, col] = 1.0
        df_bkg.loc[df_bkg[col] <= 0.0, col] = 1.0

    df_frg.to_csv(frg_path, index=False)
    df_bkg.to_csv(bkg_path, index=False)

    logging.info("Synchronizing Fermi GBM catalog triggers to foreground timestamps...")
    try:
        add_trig_gbm_to_frg(START_MONTH, END_MONTH)
    except Exception as e:
        logging.warning(f"add_trig_gbm_to_frg notice: {e}")

    logging.info(f"Configuring Poisson-FOCuS runner (mu_min={FOCUS_MU_MIN}, t_max={FOCUS_T_MAX})...")
    trigger_algo = build_focus_runner(mu_min=FOCUS_MU_MIN, t_max=FOCUS_T_MAX)
    run_trigger(START_MONTH, END_MONTH, trigger_algo)

    if trig_csv.exists():
        df_trig = pd.read_csv(trig_csv)
        num_cols = df_trig.select_dtypes(include=["number"]).columns
        max_sig = df_trig[num_cols].max().max()
        active_bins = (df_trig[num_cols] > ANALYZE_THRESHOLD).any(axis=1).sum()
        logging.info(
            f"Triggers complete. Max significance: {max_sig:.2f} sigma. "
            f"Bins > {ANALYZE_THRESHOLD} sigma: {active_bins}"
        )


# ======================================================================
# STEP 5/7: CLUSTERING & PHYSICAL EVENT EXTRACTION
# ======================================================================
def run_step_analyze() -> pd.DataFrame:
    print(f"\n[STEP 5/7] Temporal Clustering & Event Extraction...")
    analyze(START_MONTH, END_MONTH, threshold=ANALYZE_THRESHOLD, type_time="t90", type_counts="flux")

    events_csv = results_dir / f"frg_{TIMEFRAME_LABEL}" / "events_table.csv"
    if not events_csv.exists():
        logging.error(f"Events table not found at: {events_csv}")
        return pd.DataFrame()

    df_ev = pd.read_csv(events_csv)
    logging.info(f"Clustering complete. Total candidates extracted: {len(df_ev)}")
    return df_ev


# ======================================================================
# HELPER: CATALOG TEMPORAL ENRICHMENT
# ======================================================================
def enrich_events_with_catalog(df_pipeline: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches candidate events with Fermi GBM ground-truth catalog identifiers 
    and physical significance features (sigma_r*) before classification.
    """
    if df_pipeline.empty:
        return df_pipeline

    df_enriched = df_pipeline.copy()

    # 1. Merge spectral significances from triggers_table.csv if not present in events_table
    trig_table_path = results_dir / f"frg_{TIMEFRAME_LABEL}" / "triggers_table.csv"
    if trig_table_path.exists() and "sigma_r0" not in df_enriched.columns:
        df_trig_pre = pd.read_csv(trig_table_path)
        feature_cols = [c for c in ["sigma_r0", "sigma_r1", "sigma_r2", "qtl_cut_r0", "qtl_cut_r1", "qtl_cut_r2"] if c in df_trig_pre.columns]
        if "trig_ids" in df_enriched.columns and "trig_ids" in df_trig_pre.columns and feature_cols:
            df_enriched = pd.merge(df_enriched, df_trig_pre[["trig_ids"] + feature_cols], on="trig_ids", how="left")
            logging.info(f"Spectral features ({feature_cols}) merged from triggers_table.csv")

    # 2. Locate ground truth catalog (prioritize newly enriched gbm_trig_catalog.csv)
    candidate_catalogs = [
        GBM_TRIG_DB,
        DATA_DIR / "DeepGRB_catalog.csv",
        REPO_ROOT / "data" / "DeepGRB_catalog.csv"
    ]
    catalog_path = next((p for p in candidate_catalogs if p.exists() and p.stat().st_size > 0), None)
    if catalog_path is None:
        logging.warning("No ground truth catalog found for event enrichment.")
        return df_enriched

    df_cat = pd.read_csv(catalog_path)
    date_col = next((c for c in ["trigger_time", "time", "datetime", "trig_time", "met_time"] if c in df_cat.columns), None)
    if not date_col:
        return df_enriched

    # Normalize pipeline timestamps to datetime
    time_pipe_col = "start_times" if "start_times" in df_enriched.columns else "datetime"
    if time_pipe_col not in df_enriched.columns:
        return df_enriched
    df_enriched["datetime_clean"] = pd.to_datetime(df_enriched[time_pipe_col].astype(str).str.slice(0, 19), errors="coerce")

    # Normalize catalog timestamps to datetime
    is_met_cat = pd.api.types.is_numeric_dtype(df_cat[date_col])
    if not is_met_cat:
        df_cat["datetime_clean"] = pd.to_datetime(df_cat[date_col].astype(str).str.slice(0, 19), errors="coerce")
    else:
        utc_src = "trigger_time" if "trigger_time" in df_cat.columns else "time"
        if utc_src in df_cat.columns:
            df_cat["datetime_clean"] = pd.to_datetime(df_cat[utc_src].astype(str).str.slice(0, 19), errors="coerce")
        else:
            return df_enriched

    if "catalog_triggers" not in df_enriched.columns:
        df_enriched["catalog_triggers"] = np.nan

    # Perform temporal matching within MATCH_DELTA_T_SEC
    valid_cat = df_cat.dropna(subset=["datetime_clean"])
    matched_count = 0
    for _, c_row in valid_cat.iterrows():
        t_cat = c_row["datetime_clean"]
        time_diffs = (df_enriched["datetime_clean"] - t_cat).abs().dt.total_seconds()
        in_window = time_diffs <= MATCH_DELTA_T_SEC
        if in_window.any():
            best_idx = time_diffs[in_window].idxmin()
            c_name = str(c_row.get("trigger_name", c_row.get("name", c_row.get("trig_ids", "")))).strip()
            c_type = str(c_row.get("trigger_type", c_row.get("catalog_triggers", "GRB"))).strip()
            
            # Compose identifier (e.g., GRB190303240)
            if c_name and not c_name.startswith(c_type):
                cat_label = f"{c_type}_{c_name}"
            else:
                cat_label = c_name if c_name else c_type

            if pd.isna(df_enriched.loc[best_idx, "catalog_triggers"]) or df_enriched.loc[best_idx, "catalog_triggers"] == "none":
                df_enriched.loc[best_idx, "catalog_triggers"] = cat_label
                matched_count += 1

    df_enriched.drop(columns=["datetime_clean"], inplace=True, errors="ignore")
    logging.info(f"Catalog enrichment complete: {matched_count} events matched to official triggers.")
    return df_enriched


# ======================================================================
# STEP 6/7: HEURISTIC MULTICLASS CLASSIFICATION
# ======================================================================
def run_step_classification(df_ev: pd.DataFrame) -> pd.DataFrame:
    print(f"\n[STEP 6/7] Event Classification Module (Crupi Rules)...")
    if df_ev.empty:
        logging.warning("No candidate events found to classify.")
        return df_ev

    # Pre-match candidate events against official Fermi catalog
    df_ev = enrich_events_with_catalog(df_ev)

    clf = CrupiEventClassifier(df_ev)
    clf.prepare_features()
    y_pred = clf.apply_classification_logic()

    df_res = df_ev.copy()
    df_res["predicted_class"] = y_pred["predicted_class"].values

    events_csv = results_dir / f"frg_{TIMEFRAME_LABEL}" / "events_table.csv"
    df_res.to_csv(events_csv, index=False)

    print("  -> Classification distribution:")
    for cls, count in df_res["predicted_class"].value_counts().items():
        print(f"       {cls}: {count}")

    return df_res


# ======================================================================
# STEP 7/7: LOCALIZATION & BENCHMARK EVALUATION (WITH SUB-THRESHOLD ANALYSIS)
# ======================================================================
def run_step_localization_and_benchmark(df_pipeline: pd.DataFrame) -> None:
    print(f"\n[STEP 7/7] Localization & Benchmark Evaluation...")
    
    # 1. PSO angular localization on candidate events (with cache check & prediction synchronization)
    loc_table_path = results_dir / f"frg_{TIMEFRAME_LABEL}" / "events_table_loc.csv"
    if loc_table_path.exists() and loc_table_path.stat().st_size > 0:
        logging.info(f"Found existing localized table ({loc_table_path.name}). Skipping PSO localization.")
        df_loc = pd.read_csv(loc_table_path)
        
        # Synchronize updated classification and catalog triggers from df_pipeline
        sync_cols = [c for c in ["predicted_class", "catalog_triggers"] if c in df_pipeline.columns]
        if sync_cols:
            merge_key = "trig_ids" if ("trig_ids" in df_loc.columns and "trig_ids" in df_pipeline.columns) else None
            if not merge_key and "start_times" in df_loc.columns and "start_times" in df_pipeline.columns:
                merge_key = "start_times"
            
            if merge_key:
                for col in sync_cols:
                    mapping = dict(zip(df_pipeline[merge_key], df_pipeline[col]))
                    df_loc[col] = df_loc[merge_key].map(mapping).fillna(df_loc.get(col, np.nan))
            else:
                # Direct index alignment fallback
                for col in sync_cols:
                    df_loc[col] = df_pipeline[col].values
            
            # Save synchronized classifications back to localized table
            df_loc.to_csv(loc_table_path, index=False)
            logging.info(f"Synchronized fresh classifications into {loc_table_path.name}")
        
        df_pipeline = df_loc
    else:
        logging.info("Executing PSO angular localization on candidate events...")
        try:
            localize(START_MONTH, END_MONTH)
            if loc_table_path.exists():
                df_pipeline = pd.read_csv(loc_table_path)
        except Exception as e:
            logging.warning(f"Localization warning: {e}")

    # 2. Identify ground truth catalog (prioritize newly enriched gbm_trig_catalog.csv)
    candidate_catalogs = [
        GBM_TRIG_DB,
        DATA_DIR / "DeepGRB_catalog.csv",
        REPO_ROOT / "data" / "DeepGRB_catalog.csv"
    ]
    catalog_path = None
    for p in candidate_catalogs:
        if p.exists() and p.stat().st_size > 0:
            catalog_path = p
            break

    if catalog_path is None:
        logging.warning("No ground truth catalog found. Skipping benchmark.")
        return

    logging.info(f"Loading ground truth catalog from: {catalog_path.name}")
    df_cat = pd.read_csv(catalog_path)

    # Ground truth times must be UTC strings (MET-only catalogs are not supported)
    utc_col = next((c for c in ["trigger_time", "time", "datetime"]
                    if c in df_cat.columns and not pd.api.types.is_numeric_dtype(df_cat[c])), None)
    if utc_col is None:
        logging.error("Could not find a UTC timestamp column in catalog. Skipping benchmark.")
        return
    df_cat["datetime_clean"] = pd.to_datetime(df_cat[utc_col].astype(str).str.slice(0, 19), errors="coerce")

    # Explicit inclusive window, restricted to the days for which data actually exist.
    # The number of such days is the False Alarm Rate denominator.
    frg_path = pred_dir / f"frg_{TIMEFRAME_LABEL}.csv"
    valid_days = days_with_data(pd.read_csv(frg_path, usecols=["timestamp"])["timestamp"], START_DATE, END_DATE)
    total_days = len(valid_days)
    if total_days == 0:
        logging.error(f"No data days inside {START_DATE} -> {END_DATE}. Skipping benchmark.")
        return
    in_win = in_window(df_cat["datetime_clean"], START_DATE, END_DATE)
    on_data_day = df_cat["datetime_clean"].dt.strftime("%Y-%m-%d").isin(valid_days)
    df_cat_window = df_cat[in_win & on_data_day].copy()

    logging.info(
        f"Window {START_DATE} -> {END_DATE}: {int(in_win.sum())} catalog events; "
        f"{len(df_cat_window)} fall on the {total_days} days with data (FAR denominator)."
    )

    if df_pipeline.empty:
        print("  -> 0 pipeline detections in this window.")
        return

    df_pipeline = df_pipeline.copy()

    # Determine whether pipeline temporal matching is performed in MET or UTC
    use_met_match = "met" in df_pipeline.columns and ("trig_time" in df_cat_window.columns or "met_time" in df_cat_window.columns)

    if not use_met_match:
        time_pipe_col = "start_times" if "start_times" in df_pipeline.columns else "datetime"
        if time_pipe_col not in df_pipeline.columns:
            logging.error("No valid timestamp column found in pipeline results.")
            return
        df_pipeline["datetime_clean"] = pd.to_datetime(df_pipeline[time_pipe_col].astype(str).str.slice(0, 19), errors="coerce")

    matched = []
    detected_cat_indices = set()
    matched_pipeline_ids = set()
    match_details = {}

    for c_idx, c_row in df_cat_window.iterrows():
        # Compute exact time difference in seconds
        if use_met_match:
            c_met = c_row["trig_time"] if "trig_time" in c_row and pd.notna(c_row["trig_time"]) else c_row["met_time"]
            time_diffs = (df_pipeline["met"] - float(c_met)).abs()
        else:
            t_cat = c_row["datetime_clean"]
            time_diffs = (df_pipeline["datetime_clean"] - t_cat).abs().dt.total_seconds()

        # Identifier resolution
        c_name = str(c_row.get("trigger_name", c_row.get("name", c_row.get("trig_ids", "")))).replace("bn", "").replace("GRB", "").strip()
        
        id_match = pd.Series(False, index=df_pipeline.index)
        if "catalog_triggers" in df_pipeline.columns and c_name:
            id_match = df_pipeline["catalog_triggers"].astype(str).str.contains(c_name)

        # Apply the physical matching window (|delta_t| <= 1200 seconds)
        time_match = time_diffs <= MATCH_DELTA_T_SEC
        candidates = df_pipeline[id_match | time_match]

        if not candidates.empty:
            detected_cat_indices.add(c_idx)
            best_match_id = time_diffs.loc[candidates.index].idxmin()
            matched_pipeline_ids.add(best_match_id)
            p_row = df_pipeline.loc[best_match_id]
            
            raw_cat_label = str(c_row.get("trigger_type", c_row.get("catalog_triggers", "GRB")))
            match_details[best_match_id] = raw_cat_label

            matched.append({
                "pipeline_trig_id": p_row.get("trig_ids", best_match_id),
                "pipeline_label": clean_label(p_row.get("predicted_class", "UNKNOWN")),
                "official_label": clean_label(raw_cat_label),
                "delta_t_sec": time_diffs.loc[best_match_id],
            })

    df_matched = pd.DataFrame(matched)
    tp = len(detected_cat_indices)
    fn = len(df_cat_window) - tp
    fp = len(df_pipeline) - len(matched_pipeline_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / len(df_cat_window) if len(df_cat_window) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    far_per_day = fp / total_days

    # 3. Extraction & export of sub-threshold / non-cataloged candidates
    mask_matched = df_pipeline.index.isin(matched_pipeline_ids)
    unmatched_candidates = df_pipeline[~mask_matched].copy()

    # Include detections matching Crupi's ground-truth sub-threshold / untriggered flags
    subthreshold_matched = df_pipeline[
        mask_matched & 
        df_pipeline.index.map(lambda idx: any(k in match_details.get(idx, "").upper() for k in ["UNKNOWN", "LOCLPAR", "UNC"]))
    ].copy()

    df_subthreshold = pd.concat([unmatched_candidates, subthreshold_matched]).drop_duplicates()
    
    sub_csv_path = results_dir / f"frg_{TIMEFRAME_LABEL}" / "subthreshold_candidates.csv"
    export_cols = [c for c in ["met", "start_times", "duration", "predicted_class", "ra", "dec", "error_radius"] if c in df_subthreshold.columns]
    if not export_cols:
        export_cols = df_subthreshold.columns
    df_subthreshold[export_cols].to_csv(sub_csv_path, index=False)
    logging.info(f"Sub-threshold candidate catalog exported: {len(df_subthreshold)} events saved to {sub_csv_path.name}")

    # 4. Multiclass Confusion Matrix Display
    if not df_matched.empty:
        print("\n  Multiclass Confusion Matrix (Matched Events):")
        y_true = df_matched["official_label"].values
        y_pred = df_matched["pipeline_label"].values
        labels = sorted(list(set(y_true) | set(y_pred)))
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
        print(cm_df)

    # 5. Production Benchmark Summary Display
    print("\n  " + "-" * 55)
    print("  PRODUCTION BENCHMARK SUMMARY")
    print("  " + "-" * 55)
    print(f"  Pipeline Detections (P)    : {len(df_pipeline)}")
    print(f"  Catalog Ground Truth (T)   : {len(df_cat_window)}")
    print(f"  True Positives (TP)        : {tp}")
    print(f"  False Positives (FP)       : {fp}")
    print(f"  False Negatives (FN)       : {fn}")
    print(f"  Precision                  : {precision:.4f}")
    print(f"  Recall                     : {recall:.4f}")
    print(f"  F1-Score                   : {f1_score:.4f}")
    print(f"  False Alarm Rate           : {far_per_day:.2f} alerts/day")
    print(f"  Sub-threshold / New Saved  : {len(df_subthreshold)} events")
    print("  " + "-" * 55)

    # 6. Detailed Inspection of Sub-threshold Discoveries
    if not df_subthreshold.empty and "predicted_class" in df_subthreshold.columns:
        print("\n  Sub-threshold Candidate Breakdown:")
        class_counts = df_subthreshold["predicted_class"].value_counts().to_dict()
        for cls_name, count in class_counts.items():
            print(f"    - {cls_name:<10}: {count} candidate(s)")
        
        potential_grbs = df_subthreshold[df_subthreshold["predicted_class"] == "GRB"]
        if not potential_grbs.empty:
            print(f"\n  Top Sub-threshold Candidates Classified as GRB ({len(potential_grbs)} total):")
            display_cols = [c for c in ["met", "start_times", "duration", "ra", "dec", "error_radius"] if c in potential_grbs.columns]
            print(potential_grbs[display_cols].head(5).to_string(index=False))
        else:
            print("\n  Notice: Heuristic rules classified 0 sub-threshold candidates as GRB (all soft events collapsed to SF/UNC).")
        print("  " + "-" * 55)


# ======================================================================
# MAIN PIPELINE ENTRYPOINT
# ======================================================================
if __name__ == "__main__":
    print("=" * 65)
    print(f"  DEEPGRB EXECUTION ({START_MONTH} -> {END_MONTH})")
    print("=" * 65)

    events_csv = results_dir / f"frg_{TIMEFRAME_LABEL}" / "events_table.csv"

    # If candidates already exist on disk (Mac scenario / downstream analysis)
    if events_csv.exists() and events_csv.stat().st_size > 0:
        logging.info("Existing events table found. Running Step 6 (Classification) and Step 7 (Benchmark)...")
        df_events = pd.read_csv(events_csv)
        df_classified = run_step_classification(df_events)
        run_step_localization_and_benchmark(df_classified)
    else:
        # Full pipeline from scratch (ReCaS scenario for new time intervals)
        df_days = run_step_download()
        run_step_preprocess(df_days)
        run_step_neural_network()
        run_step_trigger()
        df_events = run_step_analyze()
        df_classified = run_step_classification(df_events)
        run_step_localization_and_benchmark(df_classified)

    print("\n" + "=" * 65)
    print("  DEEPGRB PIPELINE RUN COMPLETED SUCCESSFULLY")
    print("=" * 65)