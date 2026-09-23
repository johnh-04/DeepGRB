import os
import logging
import datetime
import calendar
import pandas as pd
from dateutil.relativedelta import relativedelta
from gbm.finder import ContinuousFtp
from connections.utils.config import FOLD_POSHIST, PATH_TO_SAVE, FOLD_CSPEC_POS


def download_spec(start_month, end_month, bool_overwrite=False):
    """
    Downloads CSPEC and Poshist FITS/PHA files into their respective folders.
    Checks existing files to avoid redundant downloads.
    
    :param start_month: str, starting month ('MM-YYYY', e.g. '03-2019')
    :param end_month: str, ending month excluded ('MM-YYYY', e.g. '07-2019')
    :param bool_overwrite: bool, if True forces re-downloading existing files
    :return: pandas DataFrame containing the list of scheduled days
    """
    cspec_path = os.path.join(PATH_TO_SAVE, FOLD_CSPEC_POS)
    poshist_path = os.path.join(PATH_TO_SAVE, FOLD_POSHIST)

    os.makedirs(cspec_path, exist_ok=True)
    os.makedirs(poshist_path, exist_ok=True)

    # Generate daily intervals
    date_start = datetime.date(int(start_month.split('-')[1]), int(start_month.split('-')[0]), 1)
    date_end = datetime.date(int(end_month.split('-')[1]), int(end_month.split('-')[0]), 1)
    
    days = []
    tStarts = []
    
    date_tmp = date_start
    while date_tmp < date_end:
        year = date_tmp.year
        month = date_tmp.month
        num_days = calendar.monthrange(year, month)[1]
        
        for day in range(1, num_days + 1):
            days.append(datetime.date(year, month, day).strftime("%y%m%d"))
            tStarts.append(datetime.datetime(year, month, day, 12).strftime('%Y-%m-%dT%H:%M:%S.00'))
            
        date_tmp += relativedelta(months=1)

    df_days = pd.DataFrame({'id': days, 'tStart': tStarts})
    logging.info(f"Target days to verify: {len(df_days)}")

    # Retry loop (up to 4 passes for network/FTP resilience)
    for round_idx in range(4):
        existing_files = os.listdir(cspec_path)
        
        # 14 NaI/BGO detector CSPEC files expected per day
        days_to_download = []
        for _, row in df_days.iterrows():
            day_id = row['id']
            # Count matching cspec files for this date
            day_files = [f for f in existing_files if day_id in f and f.startswith("glg_cspec")]
            if len(day_files) < 14 or bool_overwrite:
                days_to_download.append(row)

        if not days_to_download:
            logging.info("All daily CSPEC and Poshist files are present on disk.")
            break

        logging.info(f"Download round {round_idx}: {len(days_to_download)} days missing or incomplete.")

        for row in days_to_download:
            day_id = row['id']
            try:
                # Remove partial files if re-downloading
                if bool_overwrite:
                    for f in [f for f in os.listdir(cspec_path) if day_id in f]:
                        os.remove(os.path.join(cspec_path, f))

                logging.info(f"Opening FTP session for date: {day_id} (UTC: {row['tStart']})")
                ftp_daily = ContinuousFtp(utc=row['tStart'], gps=None)
                
                # Download 14 CSPEC detectors files to cspec/
                ftp_daily.get_cspec(cspec_path)
                
                # Download orbital poshist to poshist/
                ftp_daily.get_poshist(poshist_path)
                
            except Exception as e:
                logging.error(f"Failed download for day {day_id}: {e}")

    logging.info("CSPEC and Poshist data verification completed.")
    return df_days