"""
One-to-one temporal matching between pipeline events and reference triggers.

An event is the interval [start, end] (MET). A reference instant t is a candidate
for an event when start - margin <= t <= end + margin. Every event is matched to
at most one reference and vice versa: candidate pairs are assigned greedily by
increasing distance (0 inside the interval, otherwise distance to the nearest
edge; ties broken by |t - start|). References with a missing time are never
matched but are kept in the output.
"""

from typing import Sequence

import numpy as np
import pandas as pd

BINLENGTH = 4.096
PRIMARY_MARGIN = 2 * BINLENGTH


def match_one_to_one(
    ev_start: Sequence[float],
    ev_end: Sequence[float],
    ref_time: Sequence[float],
    margin: float = PRIMARY_MARGIN,
) -> pd.DataFrame:
    """
    Returns one row per reference: ref (position), event (position or -1), matched,
    dt_start (t - event start), distance (0 inside the event interval).
    """
    s = np.asarray(ev_start, dtype=float)
    e = np.asarray(ev_end, dtype=float)
    t = np.asarray(ref_time, dtype=float)

    pairs = []
    for i, ti in enumerate(t):
        if not np.isfinite(ti):
            continue
        cand = np.where((s - margin <= ti) & (ti <= e + margin))[0]
        for j in cand:
            dist = 0.0 if s[j] <= ti <= e[j] else min(abs(ti - s[j]), abs(ti - e[j]))
            pairs.append((dist, abs(ti - s[j]), i, j))
    pairs.sort()

    ref_to_ev = np.full(len(t), -1)
    used_ev = set()
    for dist, _, i, j in pairs:
        if ref_to_ev[i] == -1 and j not in used_ev:
            ref_to_ev[i] = j
            used_ev.add(j)

    matched = ref_to_ev >= 0
    dt = np.where(matched, t - s[np.clip(ref_to_ev, 0, None)] if len(s) else np.nan, np.nan)
    dist = np.full(len(t), np.nan)
    for i in np.where(matched)[0]:
        j = ref_to_ev[i]
        dist[i] = 0.0 if s[j] <= t[i] <= e[j] else min(abs(t[i] - s[j]), abs(t[i] - e[j]))
    return pd.DataFrame({"ref": np.arange(len(t)), "event": ref_to_ev, "matched": matched, "dt_start": dt, "distance": dist})


def overlap_one_to_one(a_start: Sequence[float], a_dur: Sequence[float], b_start: Sequence[float],
                       b_dur: Sequence[float], margin: float = PRIMARY_MARGIN) -> list:
    """
    One-to-one pairs (i, j, |start_i - start_j|) of overlapping intervals [start, start + duration]
    extended by +/- margin, assigned greedily by increasing |start difference|.
    """
    a0, b0 = np.asarray(a_start, dtype=float), np.asarray(b_start, dtype=float)
    a1, b1 = a0 + np.asarray(a_dur, dtype=float), b0 + np.asarray(b_dur, dtype=float)
    cand = []
    for i in range(len(a0)):
        js = np.where((b0 - margin <= a1[i] + margin) & (a0[i] - margin <= b1 + margin))[0]
        cand += [(abs(a0[i] - b0[j]), i, int(j)) for j in js]
    cand.sort()
    used_a, used_b, pairs = set(), set(), []
    for d, i, j in cand:
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            pairs.append((i, j, d))
    return pairs
