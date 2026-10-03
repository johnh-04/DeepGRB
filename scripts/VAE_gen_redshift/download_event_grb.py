"""
Batch download utility for Fermi GBM GRB burst events.
Queries the online Burst Catalog and downloads event-level CTIME or TTE high-resolution data.
"""

import logging
from pathlib import Path
from typing import List
import pandas as pd

from gbm.finder import BurstCatalog, TriggerFtp
from connections.utils.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def download_burst_events(data_type: str = "tte", max_triggers: Optional[int] = None, bool_overwrite: bool = False) -> None:
    """
    Downloads event files (TTE or CTIME) for cataloged GRBs.

    :param data_type: 'tte' for Time-Tagged Event data or 'ctime' for binned spectra
    :param max_triggers: Optional integer limit on number of bursts to fetch
    :param bool_overwrite: If True, re-downloads existing events
    """
    assert data_type in ("tte", "ctime"), "data_type must be either 'tte' or 'ctime'"
    target_dir = DATA_DIR / data_type
    target_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Retrieving official Fermi GBM Burst Catalog from HEASARC...")
    try:
        burstcat = BurstCatalog()
        df_burst = pd.DataFrame(burstcat.get_table())
    except Exception as e:
        logging.error(f"Failed to query BurstCatalog: {e}")
        return

    trigger_list = df_burst["trigger_name"].dropna().unique()
    if max_triggers:
        trigger_list = trigger_list[:max_triggers]

    logging.info(f"Target cataloged bursts to verify: {len(trigger_list)}")

    existing_files = {f.name for f in target_dir.iterdir()}

    for trig_name in trigger_list:
        clean_trig_id = str(trig_name)[2:] if str(trig_name).startswith("bn") else str(trig_name)

        # 12 NaI + 2 BGO = 14 detector files expected per event
        matching_count = sum(1 for f in existing_files if clean_trig_id in f)
        if matching_count >= 14 and not bool_overwrite:
            continue

        try:
            logging.info(f"Connecting to FTP for burst event: bn{clean_trig_id}...")
            trig_ftp = TriggerFtp(clean_trig_id)

            if data_type == "tte":
                trig_ftp.get_tte(str(target_dir))
            else:
                trig_ftp.get_ctime(str(target_dir))

            logging.info(f"Successfully downloaded {data_type.upper()} for trigger bn{clean_trig_id}")
        except Exception as err:
            logging.error(f"Download error on trigger bn{clean_trig_id}: {err}")


if __name__ == "__main__":
    download_burst_events(data_type="tte")