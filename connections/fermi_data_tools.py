import sqlite3
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from gbm.finder import BurstCatalog, TriggerCatalog
from gbm.time import Met

from connections.utils.config import PATH_GRB_TABLE, GBM_BURST_DB, GBM_TRIG_DB

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def _det_idx_to_name(idx: int, prefix_burst: bool = False) -> str:
    """Helper to convert detector numeric index (0-13) to standard notation."""
    if 0 <= idx <= 9:
        return f"NAI_0{idx}" if prefix_burst else f"n{idx}"
    if idx == 10:
        return "NAI_10" if prefix_burst else "na"
    if idx == 11:
        return "NAI_11" if prefix_burst else "nb"
    if idx == 12:
        return "b0"
    if idx == 13:
        return "b1"
    return f"unk_{idx}"


def map_det_mask(mask_str: str, burst_format: bool = False) -> str:
    """Parses binary mask string (e.g. '00100000000000') into list of active detectors."""
    if not isinstance(mask_str, str):
        return "[]"
    active_indices = [i for i, bit in enumerate(mask_str) if bit == "1"]
    mapped = [_det_idx_to_name(idx, prefix_burst=burst_format) for idx in active_indices]
    return str(mapped)


def df_burst_catalog_raw(download: bool = True) -> pd.DataFrame:
    """Downloads or loads the raw official Fermi GBM burst catalog table."""
    try:
        if download:
            logging.info("Downloading Burst Catalog from HEASARC...")
            burstcat = BurstCatalog()
            df_grb = pd.DataFrame(burstcat.get_table())
            df_grb.to_csv(PATH_GRB_TABLE, index=False)
            logging.info(f"Saved raw burst catalog to: {PATH_GRB_TABLE}")
        else:
            df_grb = pd.read_csv(PATH_GRB_TABLE)
        return df_grb
    except Exception as e:
        logging.error(f"Failed to fetch/read raw GRB catalog: {e}")
        return pd.DataFrame()


def df_burst_catalog(db_path: Path = GBM_BURST_DB) -> pd.DataFrame:
    """Fetch official Fermi GBM Burst Catalog from HEASARC, parse temporal/spectral parameters,
    and persist clean records into SQLite.
    """
    logging.info("Downloading Burst Catalog and converting timestamps to MET...")
    burstcat = BurstCatalog()
    df_grb = pd.DataFrame(burstcat.get_table())

    # Mission Elapsed Time (MET) conversion
    df_grb["tTrigger"] = df_grb["trigger_time"].apply(
        lambda x: Met(0).from_iso(str(x).replace(" ", "T")).met
    )
    df_grb["id"] = df_grb["trigger_name"].astype(str).str.slice(2)
    df_grb["trig_det"] = df_grb["bcat_detector_mask"].apply(
        lambda m: map_det_mask(m, burst_format=True)
    )

    # Durations, intervals and flux calculations
    df_grb["T90"] = df_grb["t90"]
    df_grb["T90_err"] = df_grb["t90_error"]
    df_grb["T50"] = df_grb["t50"]
    df_grb["T50_err"] = df_grb["t50_error"]
    df_grb["tStart"] = df_grb["tTrigger"] + df_grb["t90_start"]
    df_grb["tStop"] = df_grb["tStart"] + df_grb["T90"]
    df_grb["flux"] = df_grb["fluence"] / np.where(df_grb["T90"] <= 0, np.nan, df_grb["T90"])

    # Robust parsing of detection timescale (field name variation handling)
    if "trigger_timescale" in df_grb.columns:
        df_grb["trigger_timescale"] = df_grb["trigger_timescale"]
    elif "timescale" in df_grb.columns:
        df_grb["trigger_timescale"] = df_grb["timescale"]
    else:
        df_grb["trigger_timescale"] = np.nan

    # Target schema to persist
    cols_to_keep = [
        "id", "trigger_time", "tTrigger", "trigger_timescale",
        "T90", "T90_err", "T50", "T50_err",
        "tStart", "tStop", "trig_det", "fluence", "flux"
    ]

    # Filter dynamically based on available columns
    available_cols = [c for c in cols_to_keep if c in df_grb.columns]
    df_grb_clean = df_grb[available_cols].copy()

    # Safe SQLite ingestion
    with sqlite3.connect(str(db_path)) as conn:
        df_grb_clean.to_sql("GBM_GRB", conn, if_exists="replace", index=False)

    logging.info(f"Burst catalog successfully updated in: {db_path}")
    return df_grb_clean


def df_trigger_catalog(csv_path: Path = GBM_TRIG_DB) -> pd.DataFrame:
    """Fetch general trigger catalog, convert timestamps to MET, and store to CSV."""
    logging.info("Downloading General Trigger Catalog from HEASARC...")
    trigcat = TriggerCatalog()
    df_trigcat = pd.DataFrame(trigcat.get_table())

    # Convert the actual trigger event time to MET
    met_values = df_trigcat["trigger_time"].apply(
        lambda x: Met(0).from_iso(str(x).replace(" ", "T")).met
    )

    # Legacy compatibility aliases required by models/analyze.py
    df_trigcat["met_time"] = met_values
    df_trigcat["trig_time"] = met_values

    # Resolve detection timescale robustly
    if "trigger_timescale" in df_trigcat.columns:
        df_trigcat["trigger_timescale"] = df_trigcat["trigger_timescale"]
    elif "timescale" in df_trigcat.columns:
        df_trigcat["trigger_timescale"] = df_trigcat["timescale"]
    else:
        df_trigcat["trigger_timescale"] = np.nan

    # Compute met_end_time (timescale is in milliseconds)
    timescale_sec = pd.to_numeric(df_trigcat["trigger_timescale"], errors="coerce").fillna(1000.0) / 1000.0
    df_trigcat["met_end_time"] = met_values + timescale_sec

    df_trigcat["detector_mask"] = df_trigcat["detector_mask"].apply(
        lambda m: map_det_mask(m, burst_format=False)
    )

    cols_to_keep = [
        "name", "trigger_name", "met_time", "met_end_time", "trig_time", "trigger_time",
        "trigger_timescale", "trigger_type", "detector_mask"
    ]

    available_cols = [c for c in cols_to_keep if c in df_trigcat.columns]
    df_trigcat_clean = df_trigcat[available_cols].copy()
    df_trigcat_clean.to_csv(str(csv_path), index=False)

    logging.info(f"Trigger catalog successfully updated in: {csv_path}")
    return df_trigcat_clean


if __name__ == "__main__":
    # Test catalog ingestion locally
    df_burst_catalog()
    df_trigger_catalog()