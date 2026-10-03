"""
SQLite catalogue updater script.
Iterates over unlocalized trigger records, computes PSO positions,
and updates the local SQLite database safely via parametrized queries.
"""

import logging
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from gbm.data import HealPix, PosHist
from gbm.finder import ContinuousFtp
from gbm.plot import SkyPlot

from connections.utils.config import DATA_DIR, FOLD_BKG, FOLD_PRED
from models.loc.localization_class import Localization

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def update_event_catalogue_db(start_month: str = "03-2019", end_month: str = "07-2019") -> None:
    """Updates candidate trigger records with PSO coordinates in the SQLite catalogue."""
    pred_dir = DATA_DIR / FOLD_PRED
    db_file = pred_dir / "CATdatabase.db"
    loc_plots_dir = pred_dir / "loc"
    loc_plots_dir.mkdir(parents=True, exist_ok=True)

    db_uri = f"sqlite:///{db_file.resolve()}"
    engine = create_engine(db_uri)

    # Initialize table from CSV if database does not exist
    trigs_csv = pred_dir / "trigs_table.csv"
    if not db_file.exists():
        if not trigs_csv.exists():
            logging.error(f"Neither {db_file} nor {trigs_csv} exists.")
            return

        df_trig = pd.read_csv(trigs_csv)
        for c in ["ra", "dec", "ra_montecarlo", "dec_montecarlo", "ra_std", "dec_std"]:
            df_trig[c] = np.nan
        df_trig.to_sql("DEEP_TRI", con=engine, index=False, if_exists="replace")
        logging.info("Initialized DEEP_TRI table in SQLite catalogue.")

    deep_tri = pd.read_sql_table("DEEP_TRI", con=engine)
    pending_events = deep_tri[deep_tri[["ra", "dec", "ra_std", "dec_std"]].isna().any(axis=1)]

    if pending_events.empty:
        logging.info("All catalog triggers already have valid localizations. Nothing to update.")
        return

    logging.info(f"Found {len(pending_events)} triggers requiring localization updates.")

    frg_path = pred_dir / f"frg_{start_month}_{end_month}.csv"
    bkg_path = pred_dir / f"bkg_{start_month}_{end_month}.csv"
    if not frg_path.exists() or not bkg_path.exists():
        logging.error("Missing prediction matrices for localization update.")
        return

    df_frg = pd.read_csv(frg_path)
    df_bkg = pd.read_csv(bkg_path)
    df_bkg["met"] = df_frg["met"].values
    col_det = ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]

    for _, row in pending_events.iterrows():
        t_id = row["trig_ids"]
        logging.info(f"Processing trigger ID: {t_id}")

        try:
            day_name = str(row["start_times"])[2:10].replace("-", "")
            day_file = DATA_DIR / FOLD_BKG / f"{day_name}.csv"
            if not day_file.exists():
                logging.warning(f"Telemetry file {day_file} missing. Skipping.")
                continue

            df_event = pd.read_csv(day_file)
            met_event = float(row["start_met"])
            met_event_end = float(row["end_met"])

            df_frg_bkg = pd.merge(df_event, df_bkg, how="left", on=["met"], suffixes=("_frg", "_bkg"))

            col_ra = np.sort([c for c in df_frg_bkg.columns if "_ra" in c and len(c) == 5 and "n" in c])
            col_dec = np.sort([c for c in df_frg_bkg.columns if "_dec" in c and len(c) == 6 and "n" in c])

            # Select dominant energy range
            trig_dets = str(row.get("trig_dets", ""))
            energy_list = [i[-1] for i in ["_r0", "_r1", "_r2"] if i in trig_dets] or ["1"]

            e_max = -1.0
            e_selected = energy_list[0]

            for e_tmp in energy_list:
                c_frg = np.sort([c for c in df_frg_bkg.columns if "_frg" in c and "n" in c and f"_r{e_tmp}_" in c])
                c_bkg = np.sort([c for c in df_frg_bkg.columns if "_bkg" in c and "n" in c and f"_r{e_tmp}_" in c])
                diff_window = (df_frg_bkg[c_frg].values - df_frg_bkg[c_bkg].values)
                mask_w = (df_frg_bkg["met"] >= met_event - 4.0) & (df_frg_bkg["met"] <= met_event_end)
                peak_val = np.nanmax(diff_window[mask_w]) if mask_w.any() else -1.0
                if peak_val > e_max:
                    e_max = peak_val
                    e_selected = e_tmp

            col_count_frg = np.sort([c for c in df_frg_bkg.columns if "_frg" in c and "n" in c and f"_r{e_selected}_" in c])
            col_count_bkg = np.sort([c for c in df_frg_bkg.columns if "_bkg" in c and "n" in c and f"_r{e_selected}_" in c])

            df_frg_bkg[col_det] = df_frg_bkg[col_count_frg].values - df_frg_bkg[col_count_bkg].values
            mask_w = (df_frg_bkg["met"] >= met_event - 4.0) & (df_frg_bkg["met"] <= met_event_end)
            df_ev_sub = df_frg_bkg.loc[mask_w, col_det]

            if df_ev_sub.empty:
                continue

            ind_max = df_ev_sub.max(axis=1).idxmax()

            ra_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_ra], dtype=np.float64) / 180.0 * np.pi)
            dec_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_dec], dtype=np.float64) / 180.0 * np.pi)
            cnt_frg = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_count_frg], dtype=np.float64))
            cnt_bkg = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, col_count_bkg], dtype=np.float64))

            loc = Localization(ra_vals, dec_vals, cnt_frg, cnt_bkg)
            res = loc.fit()
            _ = loc.fit_conf_int(250)
            mean, cov = loc.plot(plot_show=False)

            ra_std_val = float(np.sqrt(cov[0][0])) if cov is not None else 0.0
            dec_std_val = float(np.sqrt(cov[1][1])) if cov is not None else 0.0

            # Safe parametrized SQL update query
            update_query = text("""
                UPDATE DEEP_TRI
                SET ra = :ra,
                    dec = :dec,
                    ra_montecarlo = :ra_mc,
                    dec_montecarlo = :dec_mc,
                    ra_std = :ra_std,
                    dec_std = :dec_std
                WHERE trig_ids = :t_id
            """)

            with engine.begin() as conn:
                conn.execute(update_query, {
                    "ra": float(res["ra"]),
                    "dec": float(res["dec"]),
                    "ra_mc": float(mean[0]),
                    "dec_mc": float(mean[1]),
                    "ra_std": ra_std_val,
                    "dec_std": dec_std_val,
                    "t_id": t_id
                })

            # Save skyplot
            tmp_dir = DATA_DIR / "tmp_pos"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            try:
                cont_finder = ContinuousFtp(met=int(round(met_event)))
                cont_finder.get_poshist(str(tmp_dir))
                p_files = list(tmp_dir.glob("*.fits")) + list(tmp_dir.glob("*.fit"))
                if p_files:
                    poshist = PosHist.open(str(p_files[0]))
                    skyplot = SkyPlot()
                    skyplot.add_poshist(poshist, trigtime=met_event)
                    gauss_map = HealPix.from_gaussian(float(np.round(res["ra"])), float(np.round(res["dec"])), 10.0)
                    skyplot.add_healpix(gauss_map)
                    skyplot_path = loc_plots_dir / f"out_{t_id}_loc.png"
                    plt.savefig(skyplot_path, dpi=150, bbox_inches="tight")
                    plt.close("all")
                    p_files[0].unlink(missing_ok=True)
            except Exception as e_plot:
                logging.warning(f"Could not save SkyPlot for {t_id}: {e_plot}")

        except Exception as e:
            logging.error(f"Failed updating trigger {t_id}: {e}")
            continue

    logging.info("SQLite catalogue update process completed.")


if __name__ == "__main__":
    update_event_catalogue_db()