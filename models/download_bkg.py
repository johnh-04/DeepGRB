import calendar
import datetime
import logging
import os
from pathlib import Path
from typing import List
import pandas as pd
from dateutil.relativedelta import relativedelta
from gbm.finder import ContinuousFtp

from connections.utils.config import DATA_DIR, FOLD_CSPEC_POS, FOLD_POSHIST

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def download_spec(start_month: str, end_month: str, bool_overwrite: bool = False) -> pd.DataFrame:
    """
    Downloads raw daily CSPEC and Poshist FITS files from NASA HEASARC FTP.
    Skips dates where complete sets (14 detector files) are already cached locally.

    :param start_month: Start month format 'MM-YYYY' (e.g. '03-2019')
    :param end_month: End month format 'MM-YYYY', exclusive (e.g. '07-2019')
    :param bool_overwrite: If True, forces redownloading even if complete.
    :return: DataFrame of scheduled dates.
    """
    cspec_path = DATA_DIR / FOLD_CSPEC_POS
    poshist_path = DATA_DIR / FOLD_POSHIST

    cspec_path.mkdir(parents=True, exist_ok=True)
    poshist_path.mkdir(parents=True, exist_ok=True)

    # Parse interval bounds
    start_dt = datetime.datetime.strptime(start_month, "%m-%Y").date()
    end_dt = datetime.datetime.strptime(end_month, "%m-%Y").date()

    days: List[str] = []
    t_starts: List[str] = []

    curr_dt = start_dt
    while curr_dt < end_dt:
        year = curr_dt.year
        month = curr_dt.month
        num_days = calendar.monthrange(year, month)[1]

        for d in range(1, num_days + 1):
            day_obj = datetime.date(year, month, d)
            days.append(day_obj.strftime("%y%m%d"))
            t_starts.append(datetime.datetime(year, month, d, 12, 0, 0).strftime("%Y-%m-%dT%H:%M:%S.00"))

        curr_dt += relativedelta(months=1)

    df_days = pd.DataFrame({"id": days, "tStart": t_starts})
    logging.info(f"Total operational days scheduled: {len(df_days)}")

    # Multi-pass retry loop for FTP network resilience
    for pass_idx in range(1, 5):
        existing_files = set(os.listdir(str(cspec_path)))
        days_to_download = []

        for _, row in df_days.iterrows():
            day_id = row["id"]
            # 12 NaI + 2 BGO = 14 CSPEC files per calendar day
            matched = [f for f in existing_files if day_id in f and f.startswith("glg_cspec")]
            if len(matched) < 14 or bool_overwrite:
                days_to_download.append(row)

        if not days_to_download:
            logging.info("All daily orbital CSPEC and Poshist telemetry are cached on disk.")
            break

        logging.info(f"[Pass {pass_idx}/4] Ingesting {len(days_to_download)} missing or partial days...")

        for row in days_to_download:
            day_id = row["id"]
            try:
                if bool_overwrite:
                    for f in cspec_path.glob(f"*{day_id}*"):
                        f.unlink(missing_ok=True)

                logging.info(f"Opening FTP stream for day {day_id} (UTC: {row['tStart']})")
                ftp_daily = ContinuousFtp(utc=row["tStart"], gps=None)
                ftp_daily.get_cspec(str(cspec_path))
                ftp_daily.get_poshist(str(poshist_path))

            except Exception as e:
                logging.error(f"Download failed on day {day_id}: {e}")

    logging.info("CSPEC and Poshist data synchronization process finished.")
    return df_days