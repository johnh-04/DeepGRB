"""
Data preprocessing module.
Extracts daily CSPEC binned spectra and orbital geometry, aligning count rates to continuous 4.096 s steps.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple
from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from gbm import coords
from gbm.binning.binned import rebin_by_time
from gbm.data import Cspec, PosHist

from connections.utils.config import DATA_DIR, FOLD_BKG, FOLD_CSPEC_POS

logger = logging.getLogger(__name__)


def build_table(
    df_days: pd.DataFrame,
    erange: Dict[str, List[Tuple[float, float]]],
    bool_overwrite: bool = False,
    bool_parallel: bool = False,
    n_jobs: int = 4,
) -> None:
    """
    Parses downloaded daily CSPEC and Poshist FITS files into consolidated telemetry tables.

    :param df_days: DataFrame of target observation days
    :param erange: Energy range specifications for NaI ('n') and BGO ('b') detectors
    :param bool_overwrite: If True, regenerates existing daily CSV files
    :param bool_parallel: If True, uses joblib multiprocessing across PHA files
    :param n_jobs: Maximum concurrent worker processes (safe default: 4)
    """
    bkg_dir = DATA_DIR / FOLD_BKG
    cspec_dir = DATA_DIR / FOLD_CSPEC_POS
    bkg_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting daily spectral binning and poshist consolidation...")

    for _, row in df_days.iterrows():
        day_str = str(row["id"])[:6]
        target_csv = bkg_dir / f"{day_str}.csv"

        if target_csv.exists() and not bool_overwrite:
            continue

        try:
            available_files = os.listdir(str(cspec_dir))
            pha_files = sorted([f for f in available_files if ".pha" in f and day_str in f])

            if len(pha_files) < 14:
                logger.warning(f"Incomplete detector set ({len(pha_files)}/14 files) for day {day_str}. Skipping.")
                continue

            dic_data: Dict[str, np.ndarray] = {}

            if bool_parallel:
                results = Parallel(n_jobs=min(n_jobs, 4), verbose=0)(
                    delayed(fun_lightcurve)({}, f, erange) for f in pha_files
                )
                for res_item in results:
                    for k, v in res_item.items():
                        if k != "met" or "met" not in dic_data:
                            dic_data[k] = v
            else:
                for f in pha_files:
                    dic_data = fun_lightcurve(dic_data, f, erange)

            # Locate orbital poshist file (search in cspec_dir and poshist_dir)
            pos_dir = cspec_dir.parent / "poshist"
            candidate_files = []
            if cspec_dir.exists():
                candidate_files.extend([cspec_dir / f for f in os.listdir(str(cspec_dir))])
            if pos_dir.exists():
                candidate_files.extend([pos_dir / f for f in os.listdir(str(pos_dir))])

            pos_files = sorted([f for f in candidate_files if "poshist" in f.name and day_str in f.name], reverse=True)
            if not pos_files:
                logger.warning(f"Missing Poshist file for day {day_str}. Skipping.")
                continue

            dic_data = fun_poshist(dic_data, pos_files[0])

            df_out = pd.DataFrame(dic_data)
            df_out.to_csv(target_csv, index=False)
            logger.info(f"Processed and cached day: {day_str}")

        except Exception as e:
            logger.error(f"Failed preprocessing day {day_str}: {e}")


def fun_lightcurve(
    dic_data: Dict[str, np.ndarray],
    file_tmp: str,
    erange: Dict[str, List[Tuple[float, float]]],
) -> Dict[str, np.ndarray]:
    """Integrates counts over energy channels and rebins to 4.096 s resolution."""
    cspec_dir = DATA_DIR / FOLD_CSPEC_POS
    cspec_obj = Cspec.open(str(cspec_dir / file_tmp))

    det_type = "n" if "_n" in file_tmp else ("b" if "_b" in file_tmp else None)
    if not det_type:
        raise ValueError(f"Unknown detector signature in filename: {file_tmp}")

    det_idx = file_tmp[file_tmp.find(det_type) + 1]
    lightcurve = None

    for idx, rng in enumerate(erange[det_type]):
        lc_unbinned = cspec_obj.to_lightcurve(energy_range=rng)
        lightcurve = lc_unbinned.rebin(rebin_by_time, 4.096)
        dic_data[f"{det_type}{det_idx}_r{idx}"] = lightcurve.rates

    if "met" not in dic_data and lightcurve is not None:
        dic_data["met"] = lightcurve.centroids

    return dic_data


def fun_poshist(dic_data: Dict[str, np.ndarray], file_pos: str) -> Dict[str, np.ndarray]:
    """Extracts satellite position, velocity vectors, pointing quaternions, and geomagnetic coordinates."""
    cspec_dir = DATA_DIR / FOLD_CSPEC_POS
    pos_obj = PosHist.open(str(cspec_dir / file_pos))

    met_ts = dic_data["met"]
    time_filter = (met_ts >= pos_obj._times.min()) & (met_ts <= pos_obj._times.max())

    for k in list(dic_data.keys()):
        dic_data[k] = dic_data[k][time_filter]

    met_aligned = dic_data["met"]

    # Spacecraft position and attitude quaternions
    pos_xyz = pos_obj.get_eic(met_aligned)
    dic_data["pos_x"], dic_data["pos_y"], dic_data["pos_z"] = pos_xyz[0], pos_xyz[1], pos_xyz[2]

    quats = pos_obj.get_quaternions(met_aligned)
    dic_data["a"], dic_data["b"], dic_data["c"], dic_data["d"] = quats[0], quats[1], quats[2], quats[3]

    dic_data["lat"] = pos_obj.get_latitude(met_aligned)
    dic_data["lon"] = pos_obj.get_longitude(met_aligned)
    dic_data["alt"] = pos_obj.get_altitude(met_aligned)

    vel_xyz = pos_obj.get_velocity(met_aligned)
    dic_data["vx"], dic_data["vy"], dic_data["vz"] = vel_xyz[0], vel_xyz[1], vel_xyz[2]

    ang_vel = pos_obj.get_angular_velocity(met_aligned)
    dic_data["w1"], dic_data["w2"], dic_data["w3"] = ang_vel[0], ang_vel[1], ang_vel[2]

    # Solar and Earth occultation
    dic_data["sun_vis"] = pos_obj.get_sun_visibility(met_aligned)
    sun_pos = coords.get_sun_loc(met_aligned)
    dic_data["sun_ra"], dic_data["sun_dec"] = sun_pos[0], sun_pos[1]

    dic_data["earth_r"] = pos_obj.get_earth_radius(met_aligned)
    earth_radec = pos_obj.get_geocenter_radec(met_aligned)
    dic_data["earth_ra"], dic_data["earth_dec"] = earth_radec[0], earth_radec[1]

    # Individual detector pointing and Earth limb visibility
    for det in ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb", "b0", "b1"]:
        pointing = pos_obj.detector_pointing(det, met_aligned)
        dic_data[f"{det}_ra"] = pointing[0]
        dic_data[f"{det}_dec"] = pointing[1]
        dic_data[f"{det}_vis"] = pos_obj.location_visible(pointing[0], pointing[1], met_aligned)

    # Geomagnetic coordinates
    dic_data["saa"] = pos_obj.get_saa_passage(met_aligned)
    dic_data["l"] = pos_obj.get_mcilwain_l(met_aligned)

    return dic_data