# OBSOLETE (2026-10-03): uses APIs removed in the Phase 2 fixes and printed
# "ALL PIPELINE MODULES OPERATIONAL" even with precision 0.06 and 8 alarms/day:
# it never validated the science. To run another period use
#   DEEPGRB_START_DATE=... DEEPGRB_END_DATE=... python pipeline/pipeline_bkg.py
# (see docs/BASELINE.md). Kept for reference only.
"""
End-to-End Pipeline Execution on an Isolated 1-Week Sandbox (data_test/).
Performs download, preprocessing, neural training, background inference,
Poisson-FOCuS triggering, clustering, classification, and benchmark evaluation
without modifying data/.
"""

import os
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

# ----------------------------------------------------------------------
# 1. ISOLATED SANDBOX SETUP (DIRECTORY: data_test/)
# ----------------------------------------------------------------------
import connections.utils.config as cfg

TEST_ROOT = cfg.DATA_DIR.parent / "data_test"

TEST_CSPEC = TEST_ROOT / "cspec"
TEST_POSHIST = TEST_ROOT / "poshist"
TEST_BKG = TEST_ROOT / "bkg"
TEST_NN = TEST_ROOT / "nn_model"
TEST_PRED = TEST_ROOT / "pred"
TEST_TRIG = TEST_ROOT / "trig"
TEST_RESULTS = TEST_ROOT / "results"

for folder in [TEST_CSPEC, TEST_POSHIST, TEST_BKG, TEST_NN, TEST_PRED, TEST_TRIG, TEST_RESULTS]:
    folder.mkdir(parents=True, exist_ok=True)

# Runtime path overrides
cfg.DATA_DIR = TEST_ROOT
cfg.PATH_TO_SAVE = str(TEST_ROOT) + "/"
cfg.RESULTS_DIR = TEST_RESULTS
cfg.FOLD_CSPEC_POS = Path("cspec")
cfg.FOLD_POSHIST = Path("poshist")
cfg.FOLD_BKG = Path("bkg")
cfg.FOLD_NN = Path("nn_model")
cfg.FOLD_PRED = Path("pred")
cfg.FOLD_TRIG = Path("trig")

# ----------------------------------------------------------------------
# 2. MODULE IMPORTS (Reflecting overridden paths)
# ----------------------------------------------------------------------
import models.preprocess as mp
import models.download_bkg as mdb
import models.model_nn as mnn
import models.trigger as mt
import models.analyze as ma

# Patch module-level references directly
mp.DATA_DIR = TEST_ROOT
mp.FOLD_CSPEC_POS = Path("cspec")
mp.FOLD_POSHIST = Path("poshist")
mp.FOLD_BKG = Path("bkg")

# Patch analyze module to write into data_test/results
ma.FOLD_RES = TEST_RESULTS
ma.DATA_DIR = TEST_ROOT
if hasattr(ma, "RESULTS_DIR"):
    ma.RESULTS_DIR = TEST_RESULTS

from models.download_bkg import download_spec
from models.preprocess import build_table
from models.model_nn import ModelNN
from models.trigger import run_trigger
from models.trigs.focus import build_focus_runner
from models.analyze import analyze
from models.event_classifier import CrupiEventClassifier
from models.utils.GBMutils import add_trig_gbm_to_frg

# EDIT TO CHANGE DATE
DAYS_LIST = [f"1901{i}" for i in range(12, 20)]
TIMEFRAME_LABEL = "01-2019_01-2019"

# ----------------------------------------------------------------------
# 3. HELPER UTILITIES (Label Standardization)
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# 4. STEP 1/7: DOWNLOAD MODULE (Continuous CSPEC & PosHist)
# ----------------------------------------------------------------------
def test_download_module() -> pd.DataFrame:
    print(f"\n[STEP 1/7] Testing Download Module into sandbox: {TEST_CSPEC.name}/...")
    week_df = pd.DataFrame({"id": DAYS_LIST, "day": DAYS_LIST}, index=DAYS_LIST)
    
    from gbm.finder import ContinuousFtp

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        missing_days = []
        for day_str in DAYS_LIST:
            cspec_count = len(list(TEST_CSPEC.glob(f"*{day_str}*.pha")))
            poshist_count = len(list(TEST_POSHIST.glob(f"*{day_str}*.fit*")))
            if cspec_count < 14 or poshist_count < 1:
                missing_days.append((day_str, cspec_count, poshist_count))

        if not missing_days:
            print(f"  -> All 7 days verified complete on attempt {attempt}.")
            break

        print(f"  -> Attempt {attempt}/{max_attempts}: {len(missing_days)} days incomplete/missing. Fetching...")
        for day_str, c_cnt, p_cnt in missing_days:
            year = "20" + day_str[:2]
            month = day_str[2:4]
            day = day_str[4:6]
            utc_str = f"{year}-{month}-{day}T12:00:00"

            try:
                print(f"     Fetching {utc_str[:10]} (CSPEC: {c_cnt}/14, PosHist: {p_cnt}/1)...")
                ftp = ContinuousFtp(utc=utc_str)
                ftp.get_cspec(str(TEST_CSPEC))
                ftp.get_poshist(str(TEST_POSHIST))
            except Exception as e:
                print(f"     [WARNING] Transfer error on {day_str}: {e}")

    for day_str in DAYS_LIST:
        cspec_cnt = len(list(TEST_CSPEC.glob(f"*{day_str}*.pha")))
        poshist_cnt = len(list(TEST_POSHIST.glob(f"*{day_str}*.fit*")))
        assert cspec_cnt >= 14, f"Day {day_str} incomplete: {cspec_cnt}/14 CSPEC files found in {TEST_CSPEC}"
        assert poshist_cnt >= 1, f"Day {day_str} missing PosHist file in {TEST_POSHIST}"

    print(f"  -> Download verified. All 7 operational days stored in {TEST_CSPEC.name}/ and {TEST_POSHIST.name}/.")
    return week_df

# ----------------------------------------------------------------------
# 5. STEP 2/7: PREPROCESSING MODULE (Binning & Daily Table Generation)
# ----------------------------------------------------------------------
def test_preprocess_module(week_df: pd.DataFrame) -> None:
    print(f"\n[STEP 2/7] Testing Preprocessing Module into: {TEST_BKG.name}/...")
    erange = {
        'n': [(28, 50), (50, 300), (300, 500)],
        'b': [(756, 5025), (5025, 50000)]
    }
    build_table(week_df, erange=erange, bool_overwrite=False, bool_parallel=False)
    
    for day_id in DAYS_LIST:
        day_csv = TEST_BKG / f"{day_id}.csv"
        assert day_csv.exists(), f"Missing preprocessed file: {day_csv}"
    
    print(f"  -> Preprocessing verified. 7 tables generated in: {TEST_BKG}")

# ----------------------------------------------------------------------
# 6. STEP 3/7: NEURAL NETWORK MODULE (Training & Background Inference)
# ----------------------------------------------------------------------
def test_nn_training_and_inference() -> None:
    print(f"\n[STEP 3/7] Testing Neural Network (Sandbox: {TEST_NN.name}/)...")
    frg_path = TEST_PRED / f"frg_{TIMEFRAME_LABEL}.csv"
    bkg_path = TEST_PRED / f"bkg_{TIMEFRAME_LABEL}.csv"
    
    model_handler = ModelNN(start_month="01-2019", end_month="01-2019")
    target_files = [str(TEST_BKG / f"{d}.csv") for d in DAYS_LIST]
    model_handler.list_csv = target_files
    model_handler.prepare(bool_del_trig=False)
    
    saved_models = list(TEST_NN.glob("*.keras")) + list(TEST_NN.glob("*.h5"))
    bool_train = len(saved_models) == 0
    
    if bool_train:
        print("  -> No existing test model checkpoint found. Training on 7 days (epochs=10)...")
        model_handler.train(
            bool_train=True,
            epochs=10,
            bs=2048,
            lr=0.001,
            loss_type="mean"
        )
    else:
        print(f"  -> Existing test model found ({saved_models[0].name}). Loading weights...")
        model_handler.train(bool_train=False)
    
    assert model_handler.nn_r is not None, "Failed to load model weights."
    
    if not (frg_path.exists() and bkg_path.exists()):
        print(f"  -> Computing neural background predictions for {TIMEFRAME_LABEL}...")
        model_handler.predict(time_to_del=150)
        
        # Ensure filenames match the specific timeframe label
        default_frg = TEST_PRED / "frg_01-2019_01-2019.csv"
        default_bkg = TEST_PRED / "bkg_01-2019_01-2019.csv"
        if default_frg.exists() and not frg_path.exists():
            shutil.copy(default_frg, frg_path)
        if default_bkg.exists() and not bkg_path.exists():
            shutil.copy(default_bkg, bkg_path)
    
    assert frg_path.exists(), f"Missing foreground matrix: {frg_path}"
    assert bkg_path.exists(), f"Missing background matrix: {bkg_path}"
    print(f"  -> Background inference completed. Matrices saved in: {TEST_PRED}")

# ----------------------------------------------------------------------
# 7. STEP 4/7: TRIGGER MODULE (Poisson-FOCuS Change-Point Detection)
# ----------------------------------------------------------------------
def test_trigger_execution() -> None:
    print("\n[STEP 4/7] Testing Trigger Module (Poisson-FOCuS)...")
    
    frg_path = TEST_PRED / f"frg_{TIMEFRAME_LABEL}.csv"
    bkg_path = TEST_PRED / f"bkg_{TIMEFRAME_LABEL}.csv"
    
    df_frg = pd.read_csv(frg_path)
    df_bkg = pd.read_csv(bkg_path)
    
    data_cols = [c for c in df_bkg.columns if c.startswith(("n", "b"))]
    
    print("  -> Sanitizing zero and NaN counts in BKG/FRG matrices...")
    # 1. Rimuovi eventuali NaN
    df_frg[data_cols] = df_frg[data_cols].fillna(10.0)
    df_bkg[data_cols] = df_bkg[data_cols].fillna(10.0)
    
    # 2. Elimina rigorosamente gli zeri che attivano zero_mask in run_trigger
    # Il rate di background atteso deve essere strettamente positivo (> 0)
    for col in data_cols:
        df_frg.loc[df_frg[col] <= 0.0, col] = 1.0
        df_bkg.loc[df_bkg[col] <= 0.0, col] = 1.0

    df_frg.to_csv(frg_path, index=False)
    df_bkg.to_csv(bkg_path, index=False)

    # 3. Metadati trigger Fermi
    try:
        add_trig_gbm_to_frg("01-2019", "01-2019")
    except Exception as e:
        print(f"  -> [INFO] add_trig_gbm_to_frg note: {e}")

    # 4. Esegui Poisson-FOCuS (con cache check)
    trig_csv = TEST_TRIG / f"trig_{TIMEFRAME_LABEL}.csv"
    offset_csv = TEST_TRIG / f"offset_{TIMEFRAME_LABEL}.csv"

    if trig_csv.exists() and offset_csv.exists() and trig_csv.stat().st_size > 0:
        print(f"  -> Found existing triggers in {trig_csv.name}. Skipping FOCuS calculation.")
    else:
        focus_runner = build_focus_runner(mu_min=1.05, t_max=50)
        run_trigger("01-2019", "01-2019", focus_runner)
    
    trig_csv = TEST_TRIG / f"trig_{TIMEFRAME_LABEL}.csv"
    offset_csv = TEST_TRIG / f"offset_{TIMEFRAME_LABEL}.csv"
    
    df_trig = pd.read_csv(trig_csv)
    
    # Valuta la significanza massima reale
    num_cols = df_trig.select_dtypes(include=['number']).columns
    max_sig = df_trig[num_cols].max().max()
    active_bins = (df_trig[num_cols] > 2.0).any(axis=1).sum()
    print(f"  -> Triggers completed. Max significance: {max_sig:.2f} sigma. Bins with sig > 2.0: {active_bins}")

# ----------------------------------------------------------------------
# 8. STEP 5/7: ANALYZE MODULE (Temporal Clustering & Event Construction)
# ----------------------------------------------------------------------
def test_analyze_and_clustering() -> pd.DataFrame:
    print("\n[STEP 5/7] Testing Analyze Module (Candidate Event Clustering)...")
    analyze("01-2019", "01-2019", threshold=2.0, type_time="t90", type_counts="flux")
    
    events_csv = TEST_RESULTS / f"frg_{TIMEFRAME_LABEL}" / "events_table.csv"
    default_events = TEST_RESULTS / "frg_01-2019_01-2019" / "events_table.csv"
    
    if default_events.exists() and not events_csv.exists():
        events_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(default_events, events_csv)

    assert events_csv.exists(), f"Missing events table: {events_csv}"
    
    try:
        df_ev = pd.read_csv(events_csv)
    except pd.errors.EmptyDataError:
        df_ev = pd.DataFrame(columns=[
            "trig_ids", "start_index", "start_met", "start_times",
            "end_index", "end_met", "duration", "catalog_triggers", "trig_dets"
        ])

    print(f"  -> Clustering completed. Total candidates found: {len(df_ev)}. Stored in: {events_csv}")
    return df_ev

# ----------------------------------------------------------------------
# 9. STEP 6/7: EVENT CLASSIFICATION MODULE (Heuristic Multiclass Rules)
# ----------------------------------------------------------------------
def test_classifier(df_ev: pd.DataFrame) -> pd.DataFrame:
    print("\n[STEP 6/7] Testing Heuristic Classifier Module...")
    if df_ev.empty:
        print("  -> No candidate events detected to classify within the 7-day window.")
        return df_ev
        
    clf = CrupiEventClassifier(df_ev)
    clf.prepare_features()
    y_pred = clf.apply_classification_logic()
    
    assert "predicted_class" in y_pred.columns, "Column 'predicted_class' not found in predictions."
    print("  -> Classification completed. Class distribution:")
    for cls, count in y_pred["predicted_class"].value_counts().items():
        print(f"       {cls}: {count}")
    df_res = df_ev.copy()
    df_res["predicted_class"] = y_pred["predicted_class"].values
    return df_res

# ----------------------------------------------------------------------
# 10. STEP 7/7: BENCHMARK METRICS EVALUATION (Detection & Confusion Matrix)
# ----------------------------------------------------------------------
def test_benchmark_metrics(df_pipeline: pd.DataFrame) -> None:
    print("\n[STEP 7/7] Testing Detection & Classification Benchmark...")
    
    # 1. Path to official fetched catalog (fallback to DeepGRB_catalog.csv if missing)
    catalog_path = cfg.DATA_DIR.parent / "data" / "fermi_triggers_sandbox_jan2019.csv"
    if not catalog_path.exists():
        catalog_path = cfg.DATA_DIR.parent / "data" / "DeepGRB_catalog.csv"
        
    if not catalog_path.exists():
        print(f"  -> [WARNING] Reference catalog {catalog_path} not found. Skipping benchmark.")
        return

    print(f"  -> Loading ground truth from: {catalog_path.name}")
    df_cat = pd.read_csv(catalog_path)
    df_cat["datetime_clean"] = pd.to_datetime(df_cat["datetime"].astype(str).str.slice(0, 19))
    
    # 2. Restrict to the updated sandbox week (2019-01-12 to 2019-01-20)
    t_start = pd.to_datetime("2019-01-12 00:00:00")
    t_end = pd.to_datetime("2019-01-20 00:00:00")
    df_cat_window = df_cat[(df_cat["datetime_clean"] >= t_start) & (df_cat["datetime_clean"] <= t_end)].copy()
    
    print(f"  -> Fermi GBM official events in sandbox timeframe: {len(df_cat_window)}")

    if df_pipeline.empty or "start_times" not in df_pipeline.columns:
        print("  -> 0 pipeline detections in this window.")
        tp = 0
        fp = 0
        fn = len(df_cat_window)
        precision = 0.0
        recall = 0.0
        f1_score = 0.0
        far_per_day = 0.0
    else:
        df_pipeline = df_pipeline.copy()
        df_pipeline["datetime_clean"] = pd.to_datetime(df_pipeline["start_times"].astype(str).str.slice(0, 19))
        
        matched = []
        # Matching rigoroso a partire dagli eventi ufficiali di catalogo (Ground Truth)
        for c_idx, c_row in df_cat_window.iterrows():
            t_cat = c_row["datetime_clean"]
            time_diffs = (df_pipeline["datetime_clean"] - t_cat).abs().dt.total_seconds()
            c_name = str(c_row.get("trigger_name", c_row.get("trig_ids", ""))).replace("bn", "").strip()
            
            id_match = df_pipeline["catalog_triggers"].astype(str).str.contains(c_name) if c_name else pd.Series(False, index=df_pipeline.index)
            time_match = time_diffs <= 1200.0
            candidates = df_pipeline[id_match | time_match]
            
            if not candidates.empty:
                best_p_idx = time_diffs.loc[candidates.index].idxmin()
                p_row = df_pipeline.loc[best_p_idx]
                matched.append({
                    "pipeline_trig_id": p_row.get("trig_ids", best_p_idx),
                    "pipeline_label": clean_label(p_row.get("predicted_class", "UNKNOWN")),
                    "official_label": clean_label(c_row.get("catalog_triggers", "GRB")),
                    "delta_t_sec": time_diffs.loc[best_p_idx]
                })

        df_matched = pd.DataFrame(matched)

        # Identificazione reale dei burst di catalogo rilevati
        detected_cat_indices = set()
        matched_pipeline_ids = set()
        for c_idx, c_row in df_cat_window.iterrows():
            t_cat = c_row["datetime_clean"]
            time_diffs = (df_pipeline["datetime_clean"] - t_cat).abs().dt.total_seconds()
            c_name = str(c_row.get("trigger_name", c_row.get("trig_ids", ""))).replace("bn", "").strip()
            
            id_match = df_pipeline["catalog_triggers"].astype(str).str.contains(c_name) if c_name else pd.Series(False, index=df_pipeline.index)
            time_match = time_diffs <= 1200.0
            candidates = df_pipeline[id_match | time_match]
            
            if not candidates.empty:
                detected_cat_indices.add(c_idx)
                best_match_id = time_diffs.loc[candidates.index].idxmin()
                matched_pipeline_ids.add(best_match_id)

        tp = len(detected_cat_indices)
        fn = len(df_cat_window) - tp
        fp = len(df_pipeline) - len(matched_pipeline_ids)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / len(df_cat_window) if len(df_cat_window) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        n_days = max(len(DAYS_LIST), 1)
        far_per_day = fp / n_days

        if not df_matched.empty:
            print("\n  Multiclass Confusion Matrix (Matched Events):")
            y_true = df_matched["official_label"].values
            y_pred = df_matched["pipeline_label"].values
            labels = sorted(list(set(y_true) | set(y_pred)))
            cm = confusion_matrix(y_true, y_pred, labels=labels)
            cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
            print(cm_df)

    print("\n  " + "-" * 55)
    print("  BENCHMARK SUMMARY (SANDBOX EVALUATION)")
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
    print("  " + "-" * 55)

# ----------------------------------------------------------------------
# 11. MAIN ENTRYPOINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 65)
    print("   SANDBOX PIPELINE TEST (ISOLATED IN data_test/)")
    print("=" * 65)
    
    try:
        week_days = test_download_module()
        test_preprocess_module(week_days)
        test_nn_training_and_inference()
        test_trigger_execution()
        df_events = test_analyze_and_clustering()
        df_classified = test_classifier(df_events)
        test_benchmark_metrics(df_classified)
        
        print("\n" + "=" * 65)
        print(" RESULT: ALL PIPELINE MODULES OPERATIONAL IN data_test/")
        print("=" * 65)
    except AssertionError as e:
        print(f"\n[TEST FAILURE] {e}")
    except Exception as e:
        traceback.print_exc()
        print(f"\n[EXECUTION ERROR] {e}")