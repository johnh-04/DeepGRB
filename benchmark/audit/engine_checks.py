"""
Read-only acceptance checks for Phase 2 (engine correctness) on one run folder.

1. Background reproduction (optional, --old-bkg): the run's bkg predictions are compared
   with a previous production file (for 2019: data/pred/bkg_03-2019_07-2019.csv, written by
   the same model with the upstream code) on cells that were not overwritten there.
2. SAA exclusion: no bin with r1 significance above threshold, and no event
   boundary, lies within +/-150 s of a gap > 500 s.
3. Significance coherence: for every event, S of each range is recomputed with
   an independent implementation from frg/bkg/offset and compared with the table.
4. Summary of the event table.

Writes <run>/results/engine_checks.md and prints it.

Usage (from repo root): python -m benchmark.audit.engine_checks --run <run folder> [--old-bkg <csv>]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from connections.utils.config import BASE_DIR, SAA_GAP_S, SAA_GUARD_S
from connections.utils.config import TRIGGER_THRESHOLD_SIGMA as THRESHOLD
from utils.keys import get_keys
from utils.logs import detail, setup_logging

KEYS = get_keys()
QUANTILES = np.arange(0, 21) / 20


def check_reproduction(bkg: pd.DataFrame, OLD_BKG) -> list:
    if OLD_BKG is None or not OLD_BKG.exists():
        return ["- Reference file missing: skipped."]
    old = pd.read_csv(OLD_BKG, usecols=KEYS + ["met"])
    if len(old) != len(bkg):
        return [f"- Row count differs: new {len(bkg)}, old {len(old)}: cannot compare row by row."]
    new_v = bkg[KEYS].to_numpy(dtype=float)
    old_v = old[KEYS].to_numpy(dtype=float)
    ok = np.isfinite(new_v) & np.isfinite(old_v) & (old_v != 10.0)  # 10.0 = overwritten by the old step 4
    diff = np.abs(new_v[ok] - old_v[ok])
    rel = diff / np.abs(old_v[ok])
    same_met = np.allclose(bkg["met"].to_numpy(), pd.read_csv(OLD_BKG.with_name("frg_03-2019_07-2019.csv"), usecols=["met"])["met"].to_numpy())
    return [
        f"- Cells compared: {int(ok.sum())} (same row MET as old frg: {same_met})",
        f"- |new - old|: median {np.median(diff):.3e}, 99.9th pct {np.quantile(diff, 0.999):.3e}, max {diff.max():.3e} counts/s",
        f"- relative: median {np.median(rel):.3e}, max {rel.max():.3e}",
    ]


def gap_edges(met: np.ndarray) -> np.ndarray:
    i = np.where(np.diff(met) > SAA_GAP_S)[0]
    return np.concatenate([met[i], met[i + 1]])


def check_saa(frg: pd.DataFrame, focus: pd.DataFrame, events: pd.DataFrame) -> list:
    met = frg["met"].to_numpy(dtype=float)
    edges = np.sort(gap_edges(met))

    def min_dist(t):
        pos = np.searchsorted(edges, t)
        cand = [edges[j] for j in (pos - 1, pos) if 0 <= j < len(edges)]
        return min(abs(t - c) for c in cand)

    trig_bins = np.where((focus.filter(like="_r1") > THRESHOLD).any(axis=1).to_numpy())[0]
    d_bins = np.array([min_dist(met[i]) for i in trig_bins]) if len(trig_bins) else np.array([np.inf])
    d_ev = np.array([min(min_dist(r.start_met), min_dist(r.end_met)) for r in events.itertuples()]) if len(events) else np.array([np.inf])
    return [
        f"- Gaps > {SAA_GAP_S:.0f} s: {len(edges) // 2}",
        f"- Bins with r1 > {THRESHOLD} sigma: {len(trig_bins)}; closest to a gap edge: {d_bins.min():.1f} s; "
        f"within {SAA_GUARD_S:.0f} s: {int((d_bins <= SAA_GUARD_S).sum())}",
        f"- Event boundaries closest to a gap edge: {d_ev.min():.1f} s; within {SAA_GUARD_S:.0f} s: {int((d_ev <= SAA_GUARD_S).sum())}",
        f"- RESULT: {'PASS' if (d_bins > SAA_GUARD_S).all() and (d_ev > SAA_GUARD_S).all() else 'FAIL'}",
    ]


def independent_sigma(frg: pd.DataFrame, bkg: pd.DataFrame, offset: pd.DataFrame, ev, rng: str) -> float:
    channels = [c for c in str(ev.trig_dets).split() if c.endswith(rng)]
    if not channels:
        return 0.0
    off = np.nan_to_num(offset.loc[ev.start_index].to_numpy(dtype=float), nan=0.0).min()
    lo, hi = int(max(ev.start_index + off + 1, 0)), int(ev.end_index) - 1
    n = frg.loc[lo:hi, channels].to_numpy(dtype=float)
    b = bkg.loc[lo:hi, channels].to_numpy(dtype=float)
    good = np.isfinite(n).all(axis=1) & np.isfinite(b).all(axis=1)
    n, b = n[good].sum(axis=1), b[good].sum(axis=1)
    if n.size == 0:
        return 0.0
    r = n - b
    vals = [r[r >= np.quantile(r, q)].sum() / np.sqrt(b[r >= np.quantile(r, q)].sum()) for q in QUANTILES]
    return max(0.0, max(vals))


def check_sigma(frg, bkg, offset, events) -> list:
    worst = 0.0
    for ev in events.itertuples():
        for rng in ("r0", "r1", "r2"):
            worst = max(worst, abs(independent_sigma(frg, bkg, offset, ev, rng) - getattr(ev, f"sigma_{rng}")))
    return [f"- Events checked: {len(events)} x 3 ranges; max |S_recomputed - S_table| = {worst:.2e}",
            f"- RESULT: {'PASS' if worst < 1e-6 else 'FAIL'}"]


def summary(events: pd.DataFrame) -> list:
    if events.empty:
        return ["- No events."]
    return [
        f"- Events: {len(events)}",
        f"- CE tiers: {events['CE'].value_counts().reindex(['R', 'S', 'P']).fillna(0).astype(int).to_dict()}",
        f"- Duration [s]: median {events['duration'].median():.2f}, min {events['duration'].min():.2f}, max {events['duration'].max():.2f}",
        f"- Events with S_C > 0: {int((events['sigma_C'] > 0).sum())}; with catalog trigger annotated: {int((events['catalog_triggers'].fillna('') != '').sum())}",
        f"- First/last event: {events['start_times'].iloc[0]} / {events['start_times'].iloc[-1]}",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="run folder data/runs/<start>_<end>/engine-v<N>[-<label>]")
    parser.add_argument("--old-bkg", type=Path, help="previous bkg prediction file to compare with (same rows)")
    args = parser.parse_args()
    setup_logging()
    run = args.run
    frg = pd.read_csv(run / "pred" / "frg.csv")
    bkg = pd.read_csv(run / "pred" / "bkg.csv")
    focus = pd.read_csv(run / "trig" / "trig.csv")
    offset = pd.read_csv(run / "trig" / "offset.csv")
    events = pd.read_csv(run / "results" / "events_table.csv")

    lines = [f"# Engine checks: `{run.resolve().relative_to(BASE_DIR)}`", "",
             "Generated by `python -m benchmark.audit.engine_checks` (read-only).", "",
             "## 1. Background reproduction vs previous production file", *check_reproduction(bkg, args.old_bkg), "",
             f"## 2. No triggers within {SAA_GUARD_S:.0f} s of SAA gaps", *check_saa(frg, focus, events), "",
             "## 3. Per-event significance (independent recomputation)", *check_sigma(frg, bkg, offset, events), "",
             "## 4. Event table", *summary(events), ""]
    text = "\n".join(lines)
    (run / "results" / "engine_checks.md").write_text(text, encoding="utf-8")
    detail(f"written {run / 'results' / 'engine_checks.md'}")


if __name__ == "__main__":
    main()
