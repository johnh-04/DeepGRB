import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_PRED, GBM_TRIG_DB
from connections.fermi_data_tools import df_trigger_catalog

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def update_gbm_db(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Updates the local GBM trigger catalog from HEASARC."""
    target_path = csv_path or GBM_TRIG_DB
    logging.info("Updating local GBM trigger catalog via HEASARC...")
    return df_trigger_catalog(csv_path=target_path)


def add_trig_gbm_to_frg(start_month: str, end_month: str, inter_time: float = 4.096) -> None:
    """
    Annotates the foreground matrix file with known GBM catalog triggers.

    :param start_month: Start month identifier (e.g. '03-2019')
    :param end_month: End month identifier (e.g. '07-2019')
    :param inter_time: Continuous binning time step (seconds, default 4.096 s)
    """
    frg_filename = f"frg_{start_month}_{end_month}.csv"
    frg_path = DATA_DIR / FOLD_PRED / frg_filename

    if not frg_path.exists():
        # Fallback check directly under data/
        if (DATA_DIR / frg_filename).exists():
            frg_path = DATA_DIR / frg_filename
        else:
            raise FileNotFoundError(f"Foreground file not found: {frg_path}")

    logging.info(f"Loading foreground matrix: {frg_path}")
    df_data = pd.read_csv(frg_path)
    df_data["event"] = "none"

    if not Path(GBM_TRIG_DB).exists():
        logging.warning("GBM trigger database missing locally. Downloading...")
        update_gbm_db()

    logging.info("Reading known trigger events from catalog...")
    gbm_tri = pd.read_csv(GBM_TRIG_DB)

    # Filter catalog events intersecting the foreground timeline
    min_met = df_data["met"].min()
    max_met = df_data["met"].max()
    active_triggers = gbm_tri[
        (gbm_tri["met_end_time"] >= min_met) & (gbm_tri["met_time"] <= max_met)
    ].copy()

    logging.info(f"Assigning {len(active_triggers)} catalog triggers to foreground timestamps...")

    # Efficient interval matching
    for idx, (_, row) in enumerate(active_triggers.iterrows(), start=1):
        if idx % 100 == 0:
            logging.info(f"Triggers mapped: {idx}/{len(active_triggers)}")

        t_start = row["met_time"] - inter_time
        t_end = row["met_end_time"] + inter_time
        mask = (df_data["met"] >= t_start) & (df_data["met"] <= t_end)
        df_data.loc[mask, "event"] = row["name"]

    logging.info(f"Saving updated foreground matrix to: {frg_path}")
    df_data.to_csv(frg_path, index=False)
    logging.info("Foreground catalog synchronization completed successfully.")


if __name__ == "__main__":
    # Standalone execution test: update database
    update_gbm_db()