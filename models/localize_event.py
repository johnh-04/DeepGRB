"""
Event spatial localization module.
Fits detector geometric response using Particle Swarm Optimization (PSO)
and computes Monte Carlo confidence regions projected onto HEALPix celestial maps.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

from connections.utils.config import (
    DATA_DIR,
    FOLD_BKG,
    FOLD_POSHIST,
    FOLD_PRED,
    RESULTS_DIR,
)
from gbm.coords import get_sun_loc
from gbm.data import HealPix, PosHist
from gbm.finder import ContinuousFtp
from gbm.plot import SkyPlot
from models.loc.localization_class import Localization

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def localize(
    start_month: str,
    end_month: str,
    pre_delay: float = 8.0,
    bln_only_trig_det: bool = False,
    bln_folder: bool = True,
    trig_id: Optional[int] = None,
) -> None:
    """
    Fits equatorial coordinates (RA, Dec) and error ellipses for candidate events.

    :param start_month: Start month format 'MM-YYYY'
    :param end_month: End month format 'MM-YYYY'
    :param pre_delay: Lookback buffer in seconds before event start
    :param bln_only_trig_det: If True, uses only triggered detectors for PSO fitting
    :param bln_folder: If True, caches poshist files permanently in FOLD_POSHIST
    :param trig_id: Optional single trigger ID to localize in isolation
    """
    frg_path = DATA_DIR / FOLD_PRED / f"frg_{start_month}_{end_month}.csv"
    bkg_path = DATA_DIR / FOLD_PRED / f"bkg_{start_month}_{end_month}.csv"

    df_frg = pd.read_csv(frg_path)
    df_bkg = pd.read_csv(bkg_path)

    folder_result = RESULTS_DIR / f"frg_{start_month}_{end_month}"
    events_table_path = folder_result / "events_table.csv"
    ev_tab = pd.read_csv(events_table_path)

    if trig_id is not None:
        ev_tab = ev_tab.loc[ev_tab["trig_ids"] == trig_id].copy()

    # Pre-allocate output spatial parameter columns
    for col in [
        "ra", "dec", "ra_montecarlo", "dec_montecarlo", "ra_std", "dec_std",
        "met_localisation", "ra_earth", "dec_earth", "earth_vis", "sun_vis",
        "ra_sun", "dec_sun", "l_galactic", "b_galactic", "lat_fermi",
        "lon_fermi", "alt_fermi", "l"
    ]:
        if col not in ev_tab.columns:
            ev_tab[col] = np.nan

    plot_loc_folder = folder_result / "plots" / "loc"
    plot_loc_folder.mkdir(parents=True, exist_ok=True)
    poshist_folder = DATA_DIR / FOLD_POSHIST
    poshist_folder.mkdir(parents=True, exist_ok=True)

    n_sample_montecarlo = 250
    std_sky_plot_gaussian = 10.0
    col_det = ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]

    for _, row in ev_tab.iterrows():
        t_id = row["trig_ids"]
        logging.info(f"Localizing Trigger ID {t_id} (MET Start: {row['start_met']})")

        try:
            timestamp_event = str(row["start_times"])
            met_event = float(row["start_met"])
            met_event_end = float(row["end_met"])

            # Determine dominant energy range
            trig_dets = [i.split("_")[0] for i in str(row["trig_dets"]).split()]
            rng_dets = [i.split("_")[1] for i in str(row["trig_dets"]).split() if "_" in i]
            rng_dets_cnt = [rng_dets.count(f"r{r}") for r in ["0", "1", "2"]]
            rng_max = int(np.argmax(rng_dets_cnt))

            # Load corresponding daily telemetry file
            day_event = "".join(timestamp_event[2:10].split("-"))
            daily_bkg_path = DATA_DIR / FOLD_BKG / f"{day_event}.csv"
            if not daily_bkg_path.exists():
                logging.warning(f"Telemetry file {daily_bkg_path} missing. Skipping trigger {t_id}.")
                continue

            df_event = pd.read_csv(daily_bkg_path)
            df_bkg_local = df_bkg.copy()
            df_bkg_local["met"] = df_frg["met"].values

            df_frg_bkg = pd.merge(df_event, df_bkg_local, how="left", on=["met"], suffixes=("_frg", "_bkg"))

            col_ra = np.sort([c for c in df_frg_bkg.columns if "_ra" in c and len(c) == 5 and "n" in c])
            col_dec = np.sort([c for c in df_frg_bkg.columns if "_dec" in c and len(c) == 6 and "n" in c])

            col_count_frg = np.sort([c for c in df_frg_bkg.columns if "_frg" in c and "n" in c and f"_r{rng_max}_" in c])
            col_count_bkg = np.sort([c for c in df_frg_bkg.columns if "_bkg" in c and "n" in c and f"_r{rng_max}_" in c])

            # Calculate detector residual counts
            df_frg_bkg[col_det] = df_frg_bkg[col_count_frg].values - df_frg_bkg[col_count_bkg].values

            # Filter window containing event
            mask_window = (df_frg_bkg["met"] > met_event - pre_delay) & (df_frg_bkg["met"] < met_event_end)
            df_event_window = df_frg_bkg.loc[mask_window, col_det]

            if df_event_window.empty:
                logging.warning(f"No samples found within window for trigger {t_id}")
                continue

            # Identify peak residual count sample
            max_fin = -1.0
            ind_max = None
            for det in col_det:
                cur_max = df_event_window[det].max()
                if cur_max > max_fin:
                    max_fin = cur_max
                    ind_max = df_event_window[det].idxmax()

            met_event_loc = df_frg_bkg.loc[ind_max, "met"]

            col_filter = [i for i in range(12) if col_det[i] in trig_dets] if bln_only_trig_det else list(range(12))

            ra_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, np.array(col_ra)[col_filter]], dtype=np.float64) / 180.0 * np.pi)
            dec_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, np.array(col_dec)[col_filter]], dtype=np.float64) / 180.0 * np.pi)
            cnt_frg_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, np.array(col_count_frg)[col_filter]], dtype=np.float64))
            cnt_bkg_vals = np.atleast_2d(np.asarray(df_frg_bkg.loc[ind_max, np.array(col_count_bkg)[col_filter]], dtype=np.float64))

            loc = Localization(ra_vals, dec_vals, cnt_frg_vals, cnt_bkg_vals)
            res = loc.fit()
            _ = loc.fit_conf_int(iters=n_sample_montecarlo)
            mean, cov = loc.plot(plot_show=False)

            # Retrieve orbital poshist
            met_val = int(round(float(met_event)))
            cont_finder = ContinuousFtp(met=met_val)
            poshist_name = cont_finder.ls_poshist()[0]
            poshist_target = poshist_folder / poshist_name

            if not poshist_target.exists():
                cont_finder.get_poshist(str(poshist_folder))

            poshist = PosHist.open(str(poshist_target))

            # Generate HEALPix localization sky map
            skyplot = SkyPlot()
            skyplot.add_poshist(poshist, trigtime=met_event_loc)
            gauss_map = HealPix.from_gaussian(float(np.round(res["ra"])), float(np.round(res["dec"])), std_sky_plot_gaussian)
            skyplot.add_healpix(gauss_map)

            plt.title(f"{timestamp_event[:19]}\n{np.unique(trig_dets)}\nMET: {met_event_loc:.2f}")
            plt.xlabel(str(row["catalog_triggers"]))

            out_map_path = plot_loc_folder / f"out{t_id}_loc.png"
            plt.savefig(out_map_path, bbox_inches="tight", dpi=150)
            plt.close("all")

            # Store computed spatial values
            ev_mask = ev_tab["trig_ids"] == t_id
            ev_tab.loc[ev_mask, "ra"] = np.round(res["ra"], 2)
            ev_tab.loc[ev_mask, "dec"] = np.round(res["dec"], 2)
            ev_tab.loc[ev_mask, "ra_montecarlo"] = np.round(mean[0], 2)
            ev_tab.loc[ev_mask, "dec_montecarlo"] = np.round(mean[1], 2)
            ev_tab.loc[ev_mask, "ra_std"] = np.round(cov[0][0], 2) if cov is not None else 0.0
            ev_tab.loc[ev_mask, "dec_std"] = np.round(cov[1][1], 2) if cov is not None else 0.0
            ev_tab.loc[ev_mask, "met_localisation"] = met_event_loc

            ev_tab.loc[ev_mask, "ra_earth"] = poshist.get_geocenter_radec(met_event_loc)[0]
            ev_tab.loc[ev_mask, "dec_earth"] = poshist.get_geocenter_radec(met_event_loc)[1]
            ev_tab.loc[ev_mask, "earth_vis"] = poshist.location_visible(res["ra"], res["dec"], met_event_loc)
            ev_tab.loc[ev_mask, "sun_vis"] = poshist.get_sun_visibility(met_event_loc)

            sun_coord = get_sun_loc(met_event_loc)
            ev_tab.loc[ev_mask, "ra_sun"] = sun_coord[0]
            ev_tab.loc[ev_mask, "dec_sun"] = sun_coord[1]

            sc = SkyCoord(res["ra"], res["dec"], unit="deg", frame="icrs").galactic
            ev_tab.loc[ev_mask, "l_galactic"] = sc.l.deg
            ev_tab.loc[ev_mask, "b_galactic"] = sc.b.deg

            ev_tab.loc[ev_mask, "lat_fermi"] = poshist.get_latitude(met_event_loc)
            ev_tab.loc[ev_mask, "lon_fermi"] = poshist.get_longitude(met_event_loc)
            ev_tab.loc[ev_mask, "alt_fermi"] = poshist.get_altitude(met_event_loc)
            ev_tab.loc[ev_mask, "l"] = poshist.get_mcilwain_l(met_event_loc)

        except Exception as e:
            logging.error(f"Localization failed for trigger {t_id}: {e}")
            continue

    if trig_id is None:
        out_table_path = folder_result / "events_table_loc.csv"
        ev_tab.to_csv(out_table_path, index=False)
        logging.info(f"Saved localized event table to: {out_table_path}")