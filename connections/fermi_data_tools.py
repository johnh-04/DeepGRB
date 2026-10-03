import sqlite3
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
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


def _iso_to_met(values: pd.Series) -> pd.Series:
    return values.apply(lambda x: Met(0).from_iso(str(x).replace(" ", "T")).met)


def build_trigger_catalog(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalises the HEASARC fermigtrig table.

    - met_time / met_end_time: the catalog interval 'time' -> 'end_time' (about -135 s / +480 s
      around the trigger), as in the upstream code. It is the interval excluded from the NN
      training and used to tag events with catalog triggers.
    - trig_met / trigger_time: the trigger instant, used to match events to the catalog.
    """
    df = raw.copy()
    df["met_time"] = _iso_to_met(df["time"])
    df["met_end_time"] = _iso_to_met(df["end_time"])
    df["trig_met"] = _iso_to_met(df["trigger_time"])
    df["detector_mask"] = df["detector_mask"].apply(lambda m: map_det_mask(m, burst_format=False))
    cols = [
        "name", "trigger_name", "trigger_type", "met_time", "met_end_time", "trig_met",
        "time", "end_time", "trigger_time", "trigger_timescale", "detector_mask",
    ]
    return df[[c for c in cols if c in df.columns]].sort_values("trig_met").reset_index(drop=True)


def df_trigger_catalog(csv_path: Path = GBM_TRIG_DB, raw: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Downloads the trigger catalog from HEASARC (unless `raw` is given) and stores the normalised table."""
    if raw is None:
        logging.info("Downloading General Trigger Catalog from HEASARC...")
        raw = pd.DataFrame(TriggerCatalog().get_table())
    df_trigcat_clean = build_trigger_catalog(raw)
    df_trigcat_clean.to_csv(str(csv_path), index=False)

    logging.info(f"Trigger catalog successfully updated in: {csv_path}")
    return df_trigcat_clean


if __name__ == "__main__":
    # Test catalog ingestion locally
    df_burst_catalog()
    df_trigger_catalog()