import logging
from typing import Optional, Sequence
import pandas as pd

from connections.fermi_data_tools import df_burst_catalog_raw
from models.utils.config import LIST_GRB_TABLE_COL

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def df_burst_catalog(
    download: bool = False,
    dropna: bool = True,
    select_col: Sequence[str] = LIST_GRB_TABLE_COL
) -> pd.DataFrame:
    """
    Loads and preprocesses the official Fermi GBM Burst Catalog.

    :param download: If True, queries HEASARC online before loading; otherwise loads cached table.
    :param dropna: If True, drops rows containing missing features; otherwise performs numeric imputation.
    :param select_col: Sequence of column names to extract.
    :return: Filtered pandas DataFrame.
    """
    try:
        df_grb_raw = df_burst_catalog_raw(download=download)
        if df_grb_raw.empty:
            logging.warning("Raw GRB table is empty.")
            return pd.DataFrame()

        # Validate column presence
        available_cols = [c for c in select_col if c in df_grb_raw.columns]
        missing_cols = set(select_col) - set(available_cols)
        if missing_cols:
            logging.warning(f"Columns not found in catalog and skipped: {missing_cols}")

        df_subset = df_grb_raw[available_cols].copy()

        if dropna:
            df_cleaned = df_subset.dropna(axis=0)
        else:
            # Safe numeric imputation avoiding non-numeric columns
            numeric_cols = df_subset.select_dtypes(include=["number"]).columns
            df_subset[numeric_cols] = df_subset[numeric_cols].fillna(df_subset[numeric_cols].mean())
            df_cleaned = df_subset

        return df_cleaned

    except Exception as e:
        logging.error(f"Error filtering and preparing GRB table: {e}")
        return pd.DataFrame()