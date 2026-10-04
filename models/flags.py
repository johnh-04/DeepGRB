"""
Post-processing flags (step 7; docs/ORBIT_ANALYSIS.md). They add columns to an event table and
never change the list of events:

- saa_edge_short_passage: the event start (FOCuS change point) lies within FLAG_EDGE_WINDOW_S
  before the entry or after the exit of an SAA passage whose data gap is not masked, i.e. the gap
  in the frg timeline around the passage is <= SAA_GAP_S (the masking rule of ModelNN.predict only
  acts on gaps > SAA_GAP_S).
- saa_region_proximity: Fermi's position at the event start is within FLAG_REGION_DEG of the ground
  region where the POSHIST SAA flag is set.
- near_zero_prediction: the event bins [start_index, end_index - 1], extended by FLAG_ZERO_PAD_BINS
  on each side, include a bin where the predicted background is <= 0 on some channel (network
  output clipped to zero; such bins are ignored by FOCuS and by S, but the neighbours can be
  under-predicted too).

SAA passages and the SAA region come from the POSHIST FLAGS (bit value 2), positions from SC_LAT/SC_LON.
Thresholds: connections/utils/config.py.
"""

from pathlib import Path
from typing import Sequence, Tuple

import numpy as np
import pandas as pd
from astropy.io import fits

from connections.utils.config import (FLAG_EDGE_WINDOW_S, FLAG_REGION_DEG, FLAG_REGION_GRID_DEG, FLAG_ZERO_PAD_BINS,
                                      SAA_GAP_S)
from utils.keys import get_keys
from utils.period import window_days

EDGE_WINDOW_S = FLAG_EDGE_WINDOW_S
REGION_DEG = FLAG_REGION_DEG
REGION_GRID_DEG = FLAG_REGION_GRID_DEG   # SAA region sampled on a grid of flagged positions
ZERO_PAD_BINS = FLAG_ZERO_PAD_BINS
FLAG_COLUMNS = ["saa_edge_short_passage", "saa_region_proximity", "near_zero_prediction"]


class PoshistTrack:
    """1 Hz POSHIST samples (time, lat, lon, SAA flag) of a set of days."""

    def __init__(self, files: Sequence[Path]) -> None:
        parts = []
        for f in files:
            with fits.open(f, memmap=False) as h:
                d = h[1].data
                parts.append(pd.DataFrame({"t": d["SCLK_UTC"].astype(float), "lat": d["SC_LAT"].astype(float),
                                           "lon": d["SC_LON"].astype(float), "saa": (d["FLAGS"] & 2) > 0}))
        df = pd.concat(parts, ignore_index=True).sort_values("t").drop_duplicates("t").reset_index(drop=True)
        self.t = df["t"].to_numpy()
        self.lat = df["lat"].to_numpy()
        self.lon = ((df["lon"].to_numpy() + 180.0) % 360.0) - 180.0
        self.saa = df["saa"].to_numpy()

    @classmethod
    def for_days(cls, poshist_dir: Path, days: Sequence[str]) -> "PoshistTrack":
        files = []
        for d in days:
            f = sorted(Path(poshist_dir).glob(f"glg_poshist_all_{d}_v*.fit"))
            if f:
                files.append(f[-1])
        if not files:
            raise FileNotFoundError(f"No POSHIST files in {poshist_dir} for the requested days")
        return cls(files)

    def passages(self) -> np.ndarray:
        """(entry, exit) times of SAA passages."""
        return saa_passages(self.t, self.saa)

    def region_points(self) -> np.ndarray:
        """Unique flagged ground positions on a REGION_GRID_DEG grid, as (lat, lon)."""
        pts = np.c_[self.lat[self.saa], self.lon[self.saa]]
        return np.unique(np.round(pts / REGION_GRID_DEG) * REGION_GRID_DEG, axis=0)

    def position(self, times: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        i = np.clip(np.searchsorted(self.t, times), 1, len(self.t) - 1)
        i = np.where(np.abs(times - self.t[i - 1]) <= np.abs(self.t[i] - times), i - 1, i)
        return self.lat[i], self.lon[i]


def saa_passages(t: np.ndarray, saa: np.ndarray) -> np.ndarray:
    s = saa.astype(int)
    d = np.diff(s)
    entries, exits = t[1:][d == 1], t[1:][d == -1]
    if len(s) and s[0] == 1:
        entries = np.r_[t[0], entries]
    if len(s) and s[-1] == 1:
        exits = np.r_[exits, t[-1]]
    return np.c_[entries, exits]


def unmasked_passages(passages: np.ndarray, frg_met: np.ndarray, gap_s: float = SAA_GAP_S) -> np.ndarray:
    """
    Passages whose data gap (last frg bin before the entry -> first frg bin after the exit) is <= gap_s,
    i.e. not masked by the background step. Passages at the border of the data are skipped.
    """
    met = np.sort(np.asarray(frg_met, dtype=float))
    keep = np.zeros(len(passages), dtype=bool)
    for k, (e0, e1) in enumerate(passages):
        i0 = np.searchsorted(met, e0, side="left") - 1
        i1 = np.searchsorted(met, e1, side="right")
        if 0 <= i0 and i1 < len(met):
            keep[k] = met[i1] - met[i0] <= gap_s
    return passages[keep]


def distance_to_points(lat: float, lon: float, pts: np.ndarray) -> float:
    """Great-circle distance (deg) to the nearest point (lat, lon) of pts."""
    la, lo = np.radians(lat), np.radians(lon)
    pla, plo = np.radians(pts[:, 0]), np.radians(pts[:, 1])
    c = np.sin(la) * np.sin(pla) + np.cos(la) * np.cos(pla) * np.cos(lo - plo)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))).min())


def compute_saa_flags(t_start: Sequence[float], track: PoshistTrack, frg_met: np.ndarray) -> pd.DataFrame:
    """Flag columns (and the quantities behind them) for event start times t_start (MET)."""
    t = np.asarray(t_start, dtype=float)
    short = unmasked_passages(track.passages(), frg_met)
    pts = track.region_points()
    lat, lon = track.position(t)
    dt_edge = np.full(len(t), np.nan)
    for k, tk in enumerate(t):
        if len(short):
            before = short[:, 0] - tk          # > 0: entry in the future
            after = tk - short[:, 1]           # > 0: exit in the past
            cand = np.r_[before[(before > 0) & (before <= EDGE_WINDOW_S)], after[(after > 0) & (after <= EDGE_WINDOW_S)]]
            dt_edge[k] = cand.min() if len(cand) else np.nan
    dist = np.array([distance_to_points(a, b, pts) for a, b in zip(lat, lon)])
    return pd.DataFrame({
        "saa_edge_short_passage": np.isfinite(dt_edge),
        "saa_edge_dt_s": dt_edge,
        "saa_region_proximity": dist <= REGION_DEG,
        "saa_region_dist_deg": dist,
        "fermi_lat": lat,
        "fermi_lon": lon,
    })


def zero_prediction_rows(bkg: np.ndarray) -> np.ndarray:
    """Row positions where the predicted background is <= 0 on at least one channel (NaN rows excluded)."""
    return np.where((np.asarray(bkg, dtype=float) <= 0).any(axis=1))[0]


def near_zero_prediction_flag(start_index: Sequence[int], end_index: Sequence[int], zero_rows: np.ndarray,
                              pad: int = ZERO_PAD_BINS) -> np.ndarray:
    """True when [start_index - pad, end_index - 1 + pad] contains a zero-prediction row."""
    z = np.sort(np.asarray(zero_rows, dtype=int))
    lo = np.asarray(start_index, dtype=int) - pad
    hi = np.asarray(end_index, dtype=int) - 1 + pad
    return np.searchsorted(z, hi, side="right") > np.searchsorted(z, lo, side="left")


def event_start_met(events: pd.DataFrame, met: np.ndarray, timestamp: pd.Series) -> pd.Series:
    """
    MET of the event start (FOCuS change point, column start_times_offset). Timestamps repeated at
    day boundaries (overlapping CSPEC files) map to their first occurrence; start_met is the fallback.
    """
    ts_to_met = pd.Series(np.asarray(met, dtype=float), index=pd.Series(timestamp).values)
    ts_to_met = ts_to_met[~ts_to_met.index.duplicated(keep="first")]
    return events["start_times_offset"].map(ts_to_met).fillna(events["start_met"])


def flag_events(run: Path, poshist_dir: Path, start_date: str, end_date: str) -> pd.DataFrame:
    """Flags of every event of a run (trig_ids + flag columns + the quantities behind them)."""
    run = Path(run)
    frg = pd.read_csv(run / "pred" / "frg.csv", usecols=["met", "timestamp"])
    bkg = pd.read_csv(run / "pred" / "bkg.csv", usecols=get_keys()).to_numpy(dtype=float)
    events = pd.read_csv(run / "results" / "events_table.csv")
    met = frg["met"].to_numpy(dtype=float)
    t_start = event_start_met(events, met, frg["timestamp"])
    # POSHIST of the period plus one day on each side (passages across midnight)
    days = window_days((pd.Timestamp(start_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                       (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    track = PoshistTrack.for_days(poshist_dir, days)
    flags = compute_saa_flags(t_start.to_numpy(), track, met)
    flags["near_zero_prediction"] = near_zero_prediction_flag(events["start_index"], events["end_index"],
                                                              zero_prediction_rows(bkg))
    flags.insert(0, "trig_ids", events["trig_ids"].to_numpy())
    flags.insert(1, "t_start_met", t_start.to_numpy())
    return flags


def main() -> None:
    """Writes <run>/results/events_flags.csv for an existing run (step 7 outside the pipeline); never overwrites."""
    import argparse

    from connections.utils.config import DATA_DIR, FOLD_POSHIST, run_period
    from utils.logs import detail, setup_logging
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--run", type=Path, required=True, help="run folder data/runs/<start>_<end>/engine-v<N>[-<label>]")
    args = parser.parse_args()
    setup_logging()
    out = args.run / "results" / "events_flags.csv"
    if out.exists():
        raise SystemExit(f"{out} exists: refusing to overwrite.")
    flags = flag_events(args.run, DATA_DIR / FOLD_POSHIST, *run_period(args.run))
    flags.to_csv(out, index=False)
    detail(f"written {out}: " + ", ".join(f"{c} {int(flags[c].sum())}" for c in FLAG_COLUMNS))


if __name__ == "__main__":
    main()
