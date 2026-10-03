"""
Event analysis and temporal clustering module.
Converts Poisson-FOCuS change-points into physical astrophysical event candidates.
"""

from bisect import bisect_left, bisect_right
from itertools import groupby
from math import ceil
from operator import itemgetter
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns

import connections.utils.config as cfg
from connections.utils.config import (
    GBM_BURST_DB,
    GBM_TRIG_DB,
)
from utils.keys import get_keys

BINLENGTH = 4.096
MIN_DET_NUMBER = 1
MAX_DET_NUMBER = 13


class MissingDataError(Exception):
    """Raised when telemetry or trigger data are missing."""


class GenericDisplay:
    """Base pretty-printer for pipeline event segments."""

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.gather_attrs()}>"

    def gather_attrs(self) -> str:
        attrs = "\n"
        for key, val in self.__dict__.items():
            if isinstance(val, list) and len(val) > 5:
                attrs += f"\t{key} = [{', '.join(str(v) for v in val[:5])}..]\n"
            elif isinstance(val, pd.DataFrame):
                pass
            else:
                attrs += f"\t{key} = {val}\n"
        return attrs


class Segment(GenericDisplay):
    """Represents a candidate time segment over continuous Fermi observations."""

    def __init__(
        self,
        start: int,
        end: int,
        fermi: pd.DataFrame,
        nn: pd.DataFrame,
        focus: pd.DataFrame,
        offset: pd.DataFrame,
        trigs: Optional[pd.DataFrame] = None,
    ) -> None:
        self.start = int(start)
        self.end = int(end)

        # Slice DataFrames to the specific segment interval
        self.fermi = fermi.iloc[self.start : self.end].copy().reset_index(drop=True)
        self.nn = nn.iloc[self.start : self.end].copy().reset_index(drop=True)
        self.focus = focus.iloc[self.start : self.end].copy().reset_index(drop=True)
        self.offset = offset.iloc[self.start : self.end].copy().reset_index(drop=True)

        if trigs is not None and len(trigs) > 0:
            self.trigs = trigs.iloc[self.start : self.end].copy().reset_index(drop=True)
        else:
            self.trigs = pd.DataFrame({"id": ["none"] * len(self.fermi)})

        # Residual noise estimation (MAD)
        num_cols = self.nn.select_dtypes(include=["number"]).columns
        diff = self.fermi[num_cols] - self.nn[num_cols]
        mad = stats.median_abs_deviation(diff, axis=0, scale="normal", nan_policy="omit")
        self.sigma_residual = dict(zip(num_cols, mad))

    def get_catalog_triggers(self) -> Set[str]:
        if "id" in self.trigs.columns:
            return set(self.trigs["id"].dropna()) - {"none"}
        return set()

    def did_focus_trigger(self, threshold: float, min_dets: int, max_dets: int) -> bool:
        triggers = fetch_triggers(self.focus, threshold, min_dets, max_dets)
        return len(triggers) > 0

    def plot(
        self,
        det: List[str],
        enlarge: int = 0,
        figsize: Optional[Tuple[int, int]] = None,
        legend: bool = True,
        bln_ylim: bool = True,
    ) -> Tuple[plt.Figure, Any]:
        """Plots multi-channel count rates and neural background estimates."""
        det = sorted(det)
        cmap = plt.get_cmap("viridis")
        colors = cmap(np.linspace(0.0, 0.8, 12))
        keys_det = [str(i) for i in range(10)] + ["a", "b"]
        colors_dic = dict(zip(keys_det, colors))
        custom_lines = {i: Line2D([0], [0], color=colors_dic[i], lw=4) for i in keys_det}

        fig, ax = plt.subplots(3, 1, sharex=True, figsize=figsize or (7, 6), tight_layout=True)

        for d in det:
            range_label = int(d[-1])
            mets = self.fermi["met"].values
            ax[range_label].step(mets, self.fermi[d], color=colors_dic[d[1]], where="pre", label=d[:2])
            ax[range_label].plot(mets, self.nn[d], color=colors_dic[d[1]])

        for trig in self.get_catalog_triggers():
            if trig != "none":
                mask = self.trigs["id"] == trig
                if mask.any():
                    start_m = self.fermi.loc[mask, "met"].values[0]
                    end_m = self.fermi.loc[mask, "met"].values[-1]
                    for i in range(3):
                        ax[i].axvspan(start_m, end_m, color="black", alpha=0.1)

        for i in range(3):
            if bln_ylim:
                ax[i].set_ylim(bottom=0, top=None)
            ax[i].set_ylabel(f"range {i}")

        if legend and det:
            indices = []
            for d in det:
                if d[1] not in indices:
                    indices.append(d[1])
            labels = [f"n{i}" for i in indices]
            lines = [custom_lines[i] for i in indices]
            if labels:
                fig.legend(lines, labels, framealpha=1.0, ncol=ceil(len(labels) / 4), loc="upper right")

        fig.supylabel("count rate")
        fig.supxlabel("time [MET]")
        return fig, ax


def merge(data: Sequence[Tuple[int, int]], length: int) -> List[Tuple[int, int]]:
    """Merges adjacent trigger segments closer than length time-bins."""
    if not data:
        return []
    out = []
    i = 0
    n = len(data)
    while i < n:
        j = 0
        while (i + j < n) and (data[i + j][1] - data[i][0] < length):
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
    """Identifies multi-detector trigger coincidences above threshold."""
    out = {}
    for d in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b"]:
        sub_tbl = table[get_keys(ns=[d], rs=["1"])]
        out[d] = (sub_tbl > threshold).any(axis=1)

    merged_df = pd.DataFrame(out, index=table.index)
    dets_over = merged_df.sum(axis=1)
    data = dets_over[dets_over >= min_dets_num]

    trig_segs = []
    for _, g in groupby(enumerate(data.index), lambda ix: ix[0] - ix[1]):
        indices = list(map(itemgetter(1), g))
        start, end = indices[0], indices[-1] + 1
        if (dets_over.loc[start:end] < max_dets_num).all():
            trig_segs.append((start, end))
    return trig_segs


class EventAnalyzer:
    """Encapsulates context, ground truth cross-matching, and event table production."""

    def __init__(self, start_month: str, end_month: str) -> None:
        self.start_month = start_month
        self.end_month = end_month

        frg_file = cfg.DATA_DIR / cfg.FOLD_PRED / f"frg_{start_month}_{end_month}.csv"
        bkg_file = cfg.DATA_DIR / cfg.FOLD_PRED / f"bkg_{start_month}_{end_month}.csv"
        trig_file = cfg.DATA_DIR / cfg.FOLD_TRIG / f"trig_{start_month}_{end_month}.csv"
        offset_file = cfg.DATA_DIR / cfg.FOLD_TRIG / f"offset_{start_month}_{end_month}.csv"

        self.fermi = pd.read_csv(frg_file)
        self.nn = pd.read_csv(bkg_file)
        self.focus = pd.read_csv(trig_file)
        self.offset = pd.read_csv(offset_file)

        # Residual noise estimation (MAD)
        num_cols = self.nn.select_dtypes(include=["number"]).columns
        diff = self.fermi[num_cols] - self.nn[num_cols]
        mad = stats.median_abs_deviation(diff, axis=0, scale="normal", nan_policy="omit")
        self.sigma_residual = dict(zip(num_cols, mad))

        # Crop ground-truth trigger catalog
        trig_cat = pd.read_csv(GBM_TRIG_DB).sort_values("met_time")
        min_met = self.fermi["met"].values[0]
        max_met = self.fermi["met"].values[-1]
        self.trigger_catalog = trig_cat[
            (trig_cat["met_time"] >= min_met) & (trig_cat["met_end_time"] <= max_met)
        ].copy()

        # Build ground-truth time series
        self.trigs = pd.DataFrame({
            "met": self.fermi["met"].values,
            "timestamp": self.fermi["timestamp"].values,
            "id": "none"
        })
        for _, row in self.trigger_catalog.iterrows():
            mask = (self.trigs["met"] >= row["met_time"]) & (self.trigs["met"] <= row["met_end_time"])
            self.trigs.loc[mask, "id"] = row["name"]

    def run_analysis(self, threshold: float, bln_plot: bool = False) -> bool:
        """Executes full clustering and exports candidate event tables."""
        res_dir = Path(getattr(cfg, "RESULTS_DIR", cfg.DATA_DIR / "results")) / f"frg_{self.start_month}_{self.end_month}"
        res_dir.mkdir(parents=True, exist_ok=True)

        triggers_limits = fetch_triggers(self.focus, threshold, MIN_DET_NUMBER, MAX_DET_NUMBER)
        triggers = [
            Segment(t[0], t[1], self.fermi, self.nn, self.focus, self.offset, self.trigs)
            for t in triggers_limits
        ]
        print(f"Identified {len(triggers)} trigger segments.")

        events_limits = merge(triggers_limits, length=int(600 / BINLENGTH))
        events = [
            Segment(t[0], t[1], self.fermi, self.nn, self.focus, self.offset, self.trigs)
            for t in events_limits
        ]
        print(f"Resolved {len(events)} physical events.")

        # Build tabular summary
        event_records = []
        for i, ev in enumerate(events):
            num_focus = ev.focus.select_dtypes(include=["number"])
            trig_mask = (num_focus > threshold).any()
            active_channels = " ".join(trig_mask[trig_mask].index.tolist())
            event_records.append({
                "trig_ids": i,
                "start_index": ev.start,
                "start_met": ev.fermi["met"].iloc[0],
                "start_times": ev.fermi["timestamp"].iloc[0],
                "end_index": ev.end,
                "end_met": ev.fermi["met"].iloc[-1],
                "duration": ev.fermi["met"].iloc[-1] - ev.fermi["met"].iloc[0],
                "catalog_triggers": " ".join(ev.get_catalog_triggers()),
                "trig_dets": active_channels,
            })

        cols = ["trig_ids", "start_index", "start_met", "start_times", "end_index", "end_met", "duration", "catalog_triggers", "trig_dets"]
        df_events = pd.DataFrame(event_records, columns=cols)
        df_events.to_csv(res_dir / "events_table.csv", index=False)
        print("Events table successfully saved.")
        return True


def analyze(
    start_month: str,
    end_month: str,
    threshold: float,
    type_time: str = "t90",
    type_counts: str = "flux",
    bln_plot: bool = False,
) -> bool:
    """Wrapper function preserving the original script interface."""
    analyzer = EventAnalyzer(start_month, end_month)
    return analyzer.run_analysis(threshold, bln_plot=bln_plot)