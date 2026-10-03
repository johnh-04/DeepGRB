"""
Event analysis: from Poisson-FOCuS significance tables to candidate events.

Faithful to the upstream implementation used for Crupi et al. (2023):
- trigger condition: significance > threshold in range r1 for >= MIN_DET_NUMBER detectors
  (and < MAX_DET_NUMBER, which with 12 NaI never vetoes);
- triggers closer than 600 s (in bins) are merged into events;
- segments use inclusive label slicing: the end index is one bin after the last
  triggered bin, so duration = met[end] - met[start];
- the event start is extended backwards by the FOCuS change-point offset;
- the per-event significance for each range is S = sum(N - B) / sqrt(sum(B)) over the
  triggered detectors of that range and the offset-extended interval, maximised over
  21 quantile cuts of the residuals (paper, note 2). Inputs are the rates stored in
  the frg/bkg matrices (same units as upstream).

Additions with respect to upstream: consistency C = max(S_r0, S_r1, S_r2) and the
confidence tier CE (R/S/P); bins with missing values are ignored in S instead of
turning the whole range into S = 0.
"""

import logging
from dataclasses import dataclass
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from utils.keys import get_keys

BINLENGTH = 4.096
MIN_DET_NUMBER = 1
MAX_DET_NUMBER = 13
MERGE_SECONDS = 600
QUANTILE_GRID = np.arange(0, 21) / 20
NAI_IDS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b"]
NAI_DETS = [f"n{i}" for i in NAI_IDS]
RANGES = ["r0", "r1", "r2"]

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def merge(data: Sequence[Tuple[int, int]], length: int) -> List[Tuple[int, int]]:
    """
    Merges consecutive (start, end) index pairs while the span from the first start
    to the current end stays below `length` bins.

    Example: [(1,4), (5,9), (10,11), (12,13), (20,24), (25,26)], length=10
    -> [(1,9), (10,13), (20,26)].
    """
    out = []
    i = 0
    while i < len(data):
        j = 0
        while i + j < len(data) and data[i + j][1] - data[i][0] < length:
            j += 1
        if j == 0:
            out.append((data[i][0], data[i][1]))
            i += 1
        else:
            out.append((data[i][0], data[i + j - 1][1]))
            i += j
    return out


def fetch_triggers(
    table: pd.DataFrame,
    threshold: float,
    min_dets_num: int = MIN_DET_NUMBER,
    max_dets_num: int = MAX_DET_NUMBER,
) -> List[Tuple[int, int]]:
    """
    Trigger condition on a significance table (RangeIndex, one column per channel).
    Returns (start, end) index pairs; end is one past the last triggered bin.
    """
    over = pd.DataFrame(
        {d: (table[get_keys(ns=[d], rs=["1"])] > threshold).any(axis=1) for d in NAI_IDS},
        index=table.index,
    )
    dets_over = over.sum(axis=1)
    data = dets_over[dets_over >= min_dets_num]

    segments = []
    for _, g in groupby(enumerate(data.index), lambda ix: ix[0] - ix[1]):
        idx = list(map(itemgetter(1), g))
        start, end = idx[0], idx[-1] + 1
        # inclusive label slice, as upstream: also checks the bin right after the trigger
        if (dets_over.loc[start:end] < max_dets_num).all():
            segments.append((start, end))
    return segments


@dataclass
class Segment:
    """Index limits of a trigger or event on the continuous timeline."""

    start: int
    end: int
    start_offset: int

    @property
    def end_offset(self) -> int:
        return self.end - 1

    @classmethod
    def from_limits(cls, start: int, end: int, offset: pd.DataFrame) -> "Segment":
        """Extends the start by the most negative FOCuS offset at the start bin (upstream rule)."""
        offset_ev = offset.loc[start].fillna(0).min()
        start_offset = int(max(start + offset_ev + 1, 0))
        return cls(int(start), int(end), start_offset)


def event_significance(
    frg_win: pd.DataFrame,
    bkg_win: pd.DataFrame,
    channels: Sequence[str],
    quantiles: Sequence[float] = QUANTILE_GRID,
) -> Tuple[float, float]:
    """
    S = sum(N - B) / sqrt(sum(B)) over `channels`, keeping only the bins whose summed
    residual is >= the q-quantile of the residuals; maximised over q.
    Returns (S, q). S is 0 when no cut gives a positive value.
    """
    valid = frg_win[channels].notna().all(axis=1) & bkg_win[channels].notna().all(axis=1)
    n = frg_win.loc[valid, channels].sum(axis=1).to_numpy(dtype=float)
    b = bkg_win.loc[valid, channels].sum(axis=1).to_numpy(dtype=float)
    if n.size == 0:
        return 0.0, 0.0
    diff = n - b
    best, best_q = 0.0, 0.0
    for q in quantiles:
        sel = diff >= np.quantile(diff, q)
        b_sum = b[sel].sum()
        if b_sum <= 0:
            continue
        s = diff[sel].sum() / np.sqrt(b_sum)
        if s > best:
            best, best_q = float(s), float(q)
    return best, best_q


def confidence_tier(sigmas: Dict[str, float], detectors: Sequence[str]) -> str:
    """CE tier of the paper: R = several detectors and several ranges, S = several detectors one range, P otherwise."""
    n_ranges = sum(1 for r in RANGES if sigmas.get(r, 0) > 0)
    if len(set(detectors)) > 1:
        return "R" if n_ranges > 1 else "S"
    return "P"


def catalog_trigger_ids(met: np.ndarray, trig_catalog: pd.DataFrame) -> np.ndarray:
    """Per-bin name of the catalog trigger whose (met_time, met_end_time) strictly contains the bin (upstream rule)."""
    ids = np.full(len(met), "none", dtype=object)
    if len(met) == 0:
        return ids
    start_met, end_met = np.nanmin(met), np.nanmax(met)
    cat = trig_catalog[(trig_catalog["met_time"] > start_met) & (trig_catalog["met_end_time"] < end_met)]
    for _, row in cat.sort_values("met_time").iterrows():
        ids[(met > row["met_time"]) & (met < row["met_end_time"])] = row["name"]
    return ids


def tableize(
    segments: Sequence[Segment],
    frg: pd.DataFrame,
    bkg: pd.DataFrame,
    focus: pd.DataFrame,
    trig_ids: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    """Builds the catalog table (one row per segment) with per-range significance, C and CE."""
    rows = []
    for i, s in enumerate(segments):
        foc = focus.loc[s.start:s.end]
        over = (foc > threshold).any()
        trig_channels = [c for c in over.index if over[c]]
        detectors = sorted({c.split("_")[0] for c in trig_channels}, key=NAI_DETS.index)

        frg_off = frg.loc[s.start_offset:s.end_offset]
        bkg_off = bkg.loc[s.start_offset:s.end_offset]
        sigmas, qcuts = {}, {}
        for rng in RANGES:
            channels = [c for c in trig_channels if c.endswith("_" + rng)]
            if channels:
                sigmas[rng], qcuts[rng] = event_significance(frg_off, bkg_off, channels)
            else:
                sigmas[rng], qcuts[rng] = 0.0, 0.0

        names = sorted(set(trig_ids[s.start:s.end + 1]) - {"none"})
        end_row = min(s.end, len(frg) - 1)  # a trigger running to the last bin has end == len
        rows.append({
            "trig_ids": i,
            "start_index": s.start,
            "start_met": frg.at[s.start, "met"],
            "start_times": frg.at[s.start, "timestamp"],
            "start_times_offset": frg.at[s.start_offset, "timestamp"],
            "end_index": s.end,
            "end_met": frg.at[end_row, "met"],
            "end_times": frg.at[end_row, "timestamp"],
            "duration": frg.at[end_row, "met"] - frg.at[s.start, "met"],
            "catalog_triggers": " ".join(names),
            "trig_dets": " ".join(trig_channels),
            "detectors": " ".join(detectors),
            "sigma_r0": sigmas["r0"],
            "sigma_r1": sigmas["r1"],
            "sigma_r2": sigmas["r2"],
            "sigma_C": max(sigmas.values()),
            "CE": confidence_tier(sigmas, detectors),
            "qtl_cut_r0": qcuts["r0"],
            "qtl_cut_r1": qcuts["r1"],
            "qtl_cut_r2": qcuts["r2"],
        })
    columns = [
        "trig_ids", "start_index", "start_met", "start_times", "start_times_offset",
        "end_index", "end_met", "end_times", "duration", "catalog_triggers", "trig_dets",
        "detectors", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE",
        "qtl_cut_r0", "qtl_cut_r1", "qtl_cut_r2",
    ]
    return pd.DataFrame(rows, columns=columns)


class EventAnalyzer:
    """Builds trigger and event tables from explicit input files."""

    def __init__(
        self,
        frg_path: Path,
        bkg_path: Path,
        trig_path: Path,
        offset_path: Path,
        trig_catalog_path: Path,
    ) -> None:
        self.frg = pd.read_csv(frg_path)
        self.bkg = pd.read_csv(bkg_path)
        self.focus = pd.read_csv(trig_path)
        self.offset = pd.read_csv(offset_path)
        lengths = {len(self.frg), len(self.bkg), len(self.focus), len(self.offset)}
        if len(lengths) != 1:
            raise ValueError(f"Input tables have different lengths: {lengths}")
        trig_catalog = pd.read_csv(trig_catalog_path)
        self.trig_ids = catalog_trigger_ids(self.frg["met"].to_numpy(dtype=float), trig_catalog)

    def run(self, threshold: float, out_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Writes triggers_table.csv and events_table.csv into out_dir; returns both tables."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        keys = get_keys()

        trig_limits = fetch_triggers(self.focus[keys], threshold)
        trig_segments = [Segment.from_limits(s, e, self.offset) for s, e in trig_limits]
        event_limits = merge(trig_limits, length=int(MERGE_SECONDS / BINLENGTH))
        event_segments = [Segment.from_limits(s, e, self.offset) for s, e in event_limits]
        logging.info(f"{len(trig_segments)} trigger segments -> {len(event_segments)} events (threshold {threshold})")

        args = (self.frg, self.bkg, self.focus[keys], self.trig_ids, threshold)
        triggers_table = tableize(trig_segments, *args)
        events_table = tableize(event_segments, *args)
        triggers_table.to_csv(out_dir / "triggers_table.csv", index=False)
        events_table.to_csv(out_dir / "events_table.csv", index=False)
        return triggers_table, events_table
