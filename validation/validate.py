"""
Validation of one engine run (pipeline step 8): computation only, no report text.

  A. the official Fermi/GBM trigger catalog (and the Burst Catalog for GRB T90), always;
  B. the tables of Crupi et al. (known: Table 11, unknown: Table 10), only when the run
     period overlaps the period of the paper (2019-03-01 -> 2019-07-09);

with one-to-one matching (validation/matching.py). Every number is computed here from files on
disk and written to <run>/validation/: CSV tables and summary.json. The readable report
(<run>/RESULTS.md) is written by validation/report.py from these files.

Usage (repo root):  python -m validation.validate --run data/runs/<start>_<end>/engine-v<N>[-<label>]
"""

import argparse
import json
import platform
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from validation.matching import BINLENGTH, PRIMARY_MARGIN, match_one_to_one
from connections.utils.config import (BASE_DIR, CRUPI_REFERENCE_PERIOD, GBM_BURST_DB, GBM_TRIG_DB, REFERENCE_DIR,
                                      SAA_GAP_S, SAA_GUARD_S, SENSITIVITY_MARGINS_S, TRIGGER_THRESHOLD_SIGMA, run_period)
from models.flags import FLAG_COLUMNS, event_start_met, unmasked_passages, zero_prediction_rows, PoshistTrack
from utils.fermi_time import utc_to_met
from utils.keys import get_keys
from utils.logs import detail, setup_logging
from utils.period import days_with_data, in_window, window_days
from utils.run_options import manifest_model, read_manifest

PAPER = {  # Crupi et al. 2023, 2019 period to 2019-07-09 (docs/VALIDATION.md)
    "grb_burst_catalog": 96, "grb_missing": 15, "grb_detected": 65, "grb_available": 81,
    "long_detected": 60, "long_available": 68, "short_detected": 5, "short_available": 13,
    "events_total": 100,
}
RULE_CLASSES = ["GRB", "SF", "TGF", "UNC(LP)", "GF"]
VALIDATION_DIR = "validation"


# ----------------------------------------------------------------------------- loading
class RunData:
    def __init__(self, run: Path, start_date: str, end_date: str):
        self.run = run
        self.start_date, self.end_date = start_date, end_date
        keys = get_keys()
        frg = pd.read_csv(run / "pred" / "frg.csv", usecols=["met", "timestamp"])
        bkg = pd.read_csv(run / "pred" / "bkg.csv", usecols=keys)
        self.met = frg["met"].to_numpy(dtype=float)
        self.timestamp = frg["timestamp"]
        self.valid = np.isfinite(bkg.to_numpy(dtype=float)).any(axis=1)
        self.zero_rows = zero_prediction_rows(bkg.to_numpy(dtype=float))
        focus = pd.read_csv(run / "trig" / "trig.csv", usecols=get_keys(rs=["1"]))
        self.focus_r1_max = focus.max(axis=1, skipna=True).to_numpy(dtype=float)
        self.order = np.argsort(self.met, kind="stable")
        self.met_sorted = self.met[self.order]
        gaps = np.where(np.diff(self.met) > SAA_GAP_S)[0]
        self.gap_edges = np.sort(np.concatenate([self.met[gaps], self.met[gaps + 1]]))
        self.data_days = days_with_data(self.timestamp, start_date, end_date)

        self.events = pd.read_csv(run / "results" / "events_table.csv")
        self.events["t_start"] = event_start_met(self.events, self.met, self.timestamp)
        self.events["t_end"] = self.events["end_met"]
        self.manifest = read_manifest(run)

    def _rows_near(self, t: float, half_width: float) -> np.ndarray:
        lo = np.searchsorted(self.met_sorted, t - half_width, side="left")
        hi = np.searchsorted(self.met_sorted, t + half_width, side="right")
        return self.order[lo:hi]

    def has_data(self, t: float) -> bool:
        """True if a valid (unmasked) bin lies within one bin of t."""
        if not np.isfinite(t):
            return False
        return bool(self.valid[self._rows_near(t, BINLENGTH)].any())

    def near_saa(self, t: float) -> bool:
        if not np.isfinite(t) or len(self.gap_edges) == 0:
            return False
        pos = np.searchsorted(self.gap_edges, t)
        cand = [self.gap_edges[j] for j in (pos - 1, pos) if 0 <= j < len(self.gap_edges)]
        inside_gap = (pos % 2 == 1)  # between a gap start and its end
        return inside_gap or min(abs(t - c) for c in cand) <= SAA_GUARD_S

    def focus_r1_near(self, t: float, half_width: float = 60.0) -> float:
        if not np.isfinite(t):
            return np.nan
        rows = self._rows_near(t, half_width)
        vals = self.focus_r1_max[rows]
        return float(np.nanmax(vals)) if np.isfinite(vals).any() else np.nan


def load_trigger_catalog(rd: RunData) -> pd.DataFrame:
    cat = pd.read_csv(GBM_TRIG_DB)
    cat = cat[in_window(cat["trigger_time"], rd.start_date, rd.end_date)].copy()
    cat["day"] = pd.to_datetime(cat["trigger_time"]).dt.strftime("%Y-%m-%d")
    cat = cat[cat["day"].isin(rd.data_days)].reset_index(drop=True)
    cat["has_data"] = [rd.has_data(t) for t in cat["trig_met"]]
    cat["near_saa_150s"] = [rd.near_saa(t) for t in cat["trig_met"]]
    return cat


def load_burst_catalog() -> pd.DataFrame:
    with sqlite3.connect(str(GBM_BURST_DB)) as conn:
        grb = pd.read_sql("SELECT id, trigger_time, T90 FROM GBM_GRB", conn)
    grb["name"] = "GRB" + grb["id"].astype(str)
    return grb


def crupi_reference_applies(start_date: str, end_date: str) -> bool:
    """Crupi's tables cover 2019-03-01 -> 2019-07-09: compare only when the run overlaps them."""
    lo, hi = CRUPI_REFERENCE_PERIOD
    return start_date <= hi and end_date >= lo


def load_reference(kind: str, rd: RunData) -> pd.DataFrame:
    ref = pd.read_csv(REFERENCE_DIR / f"crupi_2019_{kind}.csv")
    ref["in_window"] = in_window(ref["trigger_time_utc"], rd.start_date, rd.end_date).to_numpy()
    ref["t"] = utc_to_met(ref["trigger_time_utc"])
    ref["has_data"] = [rd.has_data(t) for t in ref["t"]]
    return ref


# ----------------------------------------------------------------------------- matching
def validate_catalog(rd: RunData, cat: pd.DataFrame, grb: pd.DataFrame, margin: float) -> Tuple[pd.DataFrame, Dict]:
    m = match_one_to_one(rd.events["t_start"], rd.events["t_end"], cat["trig_met"], margin)
    out = cat.copy()
    out["matched"] = m["matched"].to_numpy()
    out["event"] = m["event"].to_numpy()
    out["dt_start_s"] = m["dt_start"].to_numpy()
    out = out.merge(grb[["name", "T90"]], on="name", how="left")

    avail = out[out["has_data"]]
    by_type = (avail.groupby("trigger_type")["matched"].agg(["sum", "count"])
               .rename(columns={"sum": "detected", "count": "available"}))
    by_type["total_in_window"] = out.groupby("trigger_type").size()
    by_type["missing_no_data"] = by_type["total_in_window"] - by_type["available"]

    g = out[out["trigger_type"] == "GRB"]
    g_av = g[g["has_data"]]
    stats = {
        "catalog_triggers": len(out),
        "available": int(out["has_data"].sum()),
        "missing_no_data": int((~out["has_data"]).sum()),
        "near_saa_150s": int(out["near_saa_150s"].sum()),
        "detected": int(avail["matched"].sum()),
        "grb_total": len(g),
        "grb_missing": int((~g["has_data"]).sum()),
        "grb_available": len(g_av),
        "grb_detected": int(g_av["matched"].sum()),
        "long_available": int((g_av["T90"] > BINLENGTH).sum()),
        "long_detected": int(g_av.loc[g_av["T90"] > BINLENGTH, "matched"].sum()),
        "short_available": int((g_av["T90"] <= BINLENGTH).sum()),
        "short_detected": int(g_av.loc[g_av["T90"] <= BINLENGTH, "matched"].sum()),
        "grb_without_t90": int(g["T90"].isna().sum()),
    }
    return out, {"stats": stats, "by_type": by_type}


def validate_reference(rd: RunData, ref: pd.DataFrame, margin: float) -> pd.DataFrame:
    r = ref[ref["in_window"]].reset_index(drop=True).copy()
    m = match_one_to_one(rd.events["t_start"], rd.events["t_end"], r["t"], margin)
    r["matched"] = m["matched"].to_numpy()
    r["event"] = m["event"].to_numpy()
    r["dt_start_s"] = m["dt_start"].to_numpy()
    ev = rd.events
    r["our_S_r0"] = [ev.at[j, "sigma_r0"] if j >= 0 else np.nan for j in r["event"]]
    r["our_S_r1"] = [ev.at[j, "sigma_r1"] if j >= 0 else np.nan for j in r["event"]]
    r["our_S_r2"] = [ev.at[j, "sigma_r2"] if j >= 0 else np.nan for j in r["event"]]
    r["our_CE"] = [ev.at[j, "CE"] if j >= 0 else "" for j in r["event"]]
    r["our_duration_s"] = [ev.at[j, "duration"] if j >= 0 else np.nan for j in r["event"]]
    # diagnostics for unmatched references
    starts = ev["t_start"].to_numpy()
    r["nearest_event_dt_s"] = [float(starts[np.argmin(np.abs(starts - t))] - t) if len(starts) and np.isfinite(t) else np.nan for t in r["t"]]
    r["focus_r1_max_pm60s"] = [rd.focus_r1_near(t) for t in r["t"]]
    r["near_saa_150s"] = [rd.near_saa(t) for t in r["t"]]
    return r


def recall_line(df: pd.DataFrame) -> str:
    n, k = len(df), int(df["matched"].sum())
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else "0/0"


def diagnose(row) -> str:
    if row.get("covered_by_event", -1) >= 0:
        return (f"detected but merged: inside our event {int(row['covered_by_event'])}, "
                f"already matched to {row['covered_event_matched_to']} (Crupi lists them as separate events)")
    if not row["has_data"]:
        return "no valid data at the reference time (SAA mask / gap)"
    if row["near_saa_150s"]:
        return "within 150 s of an SAA gap"
    f = row["focus_r1_max_pm60s"]
    if np.isfinite(f) and f <= TRIGGER_THRESHOLD_SIGMA:
        return f"below threshold: max FOCuS r1 within ±60 s = {f:.2f} sigma"
    if np.isfinite(f):
        return f"FOCuS r1 reaches {f:.2f} sigma within ±60 s but no event covers the time (nearest event start {row['nearest_event_dt_s']:+.0f} s)"
    return "no FOCuS value nearby"


def crupi_class(name: str) -> set:
    s = str(name)
    if s.startswith("UNKNOWN:"):
        return set(s.split(":", 1)[1].strip().split("/"))
    for prefix, label in (("GRB", "GRB"), ("SFL", "SF"), ("TGF", "TGF"), ("LOCLPAR", "UNC(LP)"), ("TRANSNT", "UNC"), ("UNCERT", "UNC"), ("SGR", "UNC")):
        if s.startswith(prefix):
            return {label}
    return {"UNC"}


# ----------------------------------------------------------------------------- run metadata
def run_model_bundle(run: Path) -> str:
    """Bundle that produced the run's predictions (the source run's one when pred/ is reused)."""
    return manifest_model(read_manifest(run)).get("bundle") or "?"


def model_description(bundle: str) -> str:
    """Training seed of a model bundle, from its metadata.json."""
    meta_path = BASE_DIR / bundle / "metadata.json"
    if not meta_path.exists():
        return "bundle metadata not found"
    meta = json.loads(meta_path.read_text())
    if "seed" in meta:
        return f"training seed {meta['seed']} (from the bundle metadata.json)"
    return "training seed not recorded in the bundle metadata"


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


# ----------------------------------------------------------------------------- sections
def classification_tables(rd: RunData, known: pd.DataFrame, unknown: pd.DataFrame) -> Optional[Dict]:
    """Rule flags and predicted class against Crupi's tentative classes (matched events only)."""
    path = rd.run / "results" / "events_classified.csv"
    if not path.exists():
        return None
    cls = pd.read_csv(path).set_index("trig_ids")
    rows = []
    for kind, ref in (("known", known), ("unknown", unknown)):
        for _, r in ref[ref["matched"]].iterrows():
            tid = rd.events.at[r["event"], "trig_ids"]
            row = {"set": kind, "id": r["id"], "crupi_class": "/".join(sorted(crupi_class(r["catalog_name"]))),
                   "predicted_class": cls.at[tid, "predicted_class"]}
            for c in RULE_CLASSES:
                row[f"rule_{c}"] = bool(cls.at[tid, f"rule_{c}"]) if f"rule_{c}" in cls.columns else np.nan
            rows.append(row)
    df = pd.DataFrame(rows)
    out = {"table": df, "rules": pd.DataFrame(), "confusion": pd.DataFrame(), "n": len(df), "correct": 0, "single": 0}
    if df.empty:
        return out
    truth = df["crupi_class"].str.split("/")
    ovr = []
    for c in RULE_CLASSES:
        if f"rule_{c}" not in df.columns:
            continue
        t = truth.apply(lambda s: c in s)
        pr = df[f"rule_{c}"].astype(bool)
        tp, fp, fn = int((t & pr).sum()), int((~t & pr).sum()), int((t & ~pr).sum())
        ovr.append({"rule": c, "Crupi positives": int(t.sum()), "rule flags": int(pr.sum()), "TP": tp, "FP": fp, "FN": fn,
                    "precision": tp / (tp + fp) if tp + fp else np.nan, "recall": tp / (tp + fn) if tp + fn else np.nan})
    single = df[~df["crupi_class"].str.contains("/")]
    labels = sorted(set(single["crupi_class"]) | set(single["predicted_class"]))
    cm = pd.crosstab(pd.Categorical(single["crupi_class"], categories=labels),
                     pd.Categorical(single["predicted_class"], categories=labels), dropna=False)
    cm.index.name, cm.columns.name = "Crupi class", "predicted"
    correct = df.apply(lambda r: r["predicted_class"] in r["crupi_class"].split("/"), axis=1)
    out.update(rules=pd.DataFrame(ovr), confusion=cm, correct=int(correct.sum()), single=len(single))
    return out


def significance_vs_crupi(known: pd.DataFrame, unknown: pd.DataFrame) -> pd.DataFrame:
    """Ratio of our S to Crupi's (matched events with a numeric reference S)."""
    both = pd.concat([known[known["matched"]], unknown[unknown["matched"]]])
    rows = []
    for rng in ("r0", "r1", "r2"):
        ref_s = both[f"S_{rng}"].astype(str).str.strip()
        sel = (ref_s != ">10") & (ref_s.astype(str) != "0") & (ref_s != "0.0")
        sel &= both[f"our_S_{rng}"] > 0
        ratio = both.loc[sel, f"our_S_{rng}"] / ref_s[sel].astype(float)
        rows.append({"range": rng, "events": int(sel.sum()), "median S_ours/S_Crupi": ratio.median() if len(ratio) else np.nan,
                     "16th pct": ratio.quantile(0.16) if len(ratio) else np.nan, "84th pct": ratio.quantile(0.84) if len(ratio) else np.nan})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- main computation
def validate_run(run: Path, poshist_dir: Path) -> Dict:
    """Validates a run and writes <run>/validation/ (CSV + summary.json). Returns the summary."""
    run = Path(run).resolve()
    start_date, end_date = run_period(run)
    out = run / VALIDATION_DIR
    out.mkdir(parents=True, exist_ok=True)
    rd = RunData(run, start_date, end_date)
    ev = rd.events
    with_crupi = crupi_reference_applies(start_date, end_date)

    flags_path = run / "results" / "events_flags.csv"
    if not flags_path.exists():
        raise FileNotFoundError(f"{flags_path} missing: run step 7 (flags) first.")
    flags = pd.read_csv(flags_path, float_precision="round_trip")
    if flags["trig_ids"].tolist() != ev["trig_ids"].tolist():
        raise ValueError(f"{flags_path} does not match the event table of {run.name}")

    cat = load_trigger_catalog(rd)
    grb = load_burst_catalog()
    cat_m, cat_stats = validate_catalog(rd, cat, grb, PRIMARY_MARGIN)
    cat_m.to_csv(out / "matches_gbm_catalog.csv", index=False)
    cat_stats["by_type"].reset_index()[["trigger_type", "total_in_window", "missing_no_data", "available", "detected"]] \
        .to_csv(out / "gbm_by_type.csv", index=False)

    empty_ref = pd.DataFrame(columns=["id", "t", "matched", "event", "CE"])
    if with_crupi:
        known_all, unknown_all = load_reference("known", rd), load_reference("unknown", rd)
        known = validate_reference(rd, known_all, PRIMARY_MARGIN)
        unknown = validate_reference(rd, unknown_all, PRIMARY_MARGIN)
        # which reference took each event (known and unknown are matched separately)
        taken = {}
        for r in (known, unknown):
            for _, x in r[r["matched"]].iterrows():
                taken.setdefault(int(x["event"]), []).append(x["id"])
        for r in (known, unknown):
            cov, cov_to = [], []
            for _, x in r.iterrows():
                inside = ev.index[(ev["t_start"] - PRIMARY_MARGIN <= x["t"]) & (x["t"] <= ev["t_end"] + PRIMARY_MARGIN)]
                j = int(inside[0]) if (not x["matched"] and len(inside)) else -1
                cov.append(int(ev.at[j, "trig_ids"]) if j >= 0 else -1)
                cov_to.append(" ".join(taken.get(j, [])) if j >= 0 else "")
            r["covered_by_event"], r["covered_event_matched_to"] = cov, cov_to
            r["diagnosis"] = [diagnose(x) if not x["matched"] else "" for _, x in r.iterrows()]
        known.to_csv(out / "matches_crupi_known.csv", index=False)
        unknown.to_csv(out / "matches_crupi_unknown.csv", index=False)
    else:
        known_all = unknown_all = known = unknown = empty_ref

    ev = ev.copy()
    ev["match_gbm"] = ev.index.isin(set(cat_m.loc[cat_m["matched"], "event"]))
    ev["match_crupi_known"] = ev.index.isin(set(known.loc[known["matched"].astype(bool), "event"]))
    ev["match_crupi_unknown"] = ev.index.isin(set(unknown.loc[unknown["matched"].astype(bool), "event"]))
    ev["counterpart"] = ev["match_gbm"] | ev["match_crupi_known"] | ev["match_crupi_unknown"]
    flag_cols = [c for c in flags.columns if c not in ("trig_ids", "t_start_met")]
    ev = pd.concat([ev, flags[flag_cols].set_index(ev.index)], axis=1)
    ev[["trig_ids", "start_times", "duration", "detectors", "sigma_C", "CE", "counterpart", "match_gbm",
        "match_crupi_known", "match_crupi_unknown"] + flag_cols].to_csv(out / "events_counterparts.csv", index=False)

    flag_rows = []
    groups = (("matched to Crupi/GBM", ev[ev["counterpart"]]), ("without counterpart", ev[~ev["counterpart"]]), ("all", ev))
    for label, sub in groups:
        flag_rows.append({"events": label, "n": len(sub), **{c: int(sub[c].sum()) for c in FLAG_COLUMNS},
                          "at least one": int(sub[FLAG_COLUMNS].any(axis=1).sum())})
    pd.DataFrame(flag_rows).to_csv(out / "flag_summary.csv", index=False)

    lonely = ev[~ev["counterpart"]].copy()
    edges = rd.gap_edges
    lonely["dist_saa_gap_s"] = [float(np.min(np.abs(edges - t))) if len(edges) else np.nan for t in lonely["t_start"]]
    if with_crupi:
        ref_t = np.concatenate([known_all["t"].to_numpy(), unknown_all["t"].to_numpy()])
        ref_id = np.concatenate([known_all["id"].to_numpy(), unknown_all["id"].to_numpy()])
        nearest = [int(np.argmin(np.abs(ref_t - t))) for t in lonely["t_start"]]
        lonely["nearest_crupi"] = [ref_id[i] for i in nearest]
        lonely["nearest_crupi_dt_h"] = [(ref_t[i] - t) / 3600 for i, t in zip(nearest, lonely["t_start"])]
    cls_path = run / "results" / "events_classified.csv"
    extra = ["l", "lat_fermi", "lon_fermi", "predicted_class"]
    if cls_path.exists():
        lonely = lonely.merge(pd.read_csv(cls_path)[["trig_ids"] + extra], on="trig_ids", how="left")
    lonely_cols = ["trig_ids", "start_times", "duration", "detectors", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE",
                   "catalog_triggers", "dist_saa_gap_s", "nearest_crupi", "nearest_crupi_dt_h"] + FLAG_COLUMNS \
        + [c for c in extra if c in lonely.columns]
    lonely[[c for c in lonely_cols if c in lonely.columns]].to_csv(out / "events_without_counterpart.csv", index=False)

    # sensitivity to the matching rule
    sens = []
    for label, margin in SENSITIVITY_MARGINS_S.items():
        _, cs = validate_catalog(rd, cat, grb, margin)
        row = {"margin": label, "GBM detected/available": f"{cs['stats']['detected']}/{cs['stats']['available']}",
               "GRB": f"{cs['stats']['grb_detected']}/{cs['stats']['grb_available']}"}
        if with_crupi:
            row["Crupi known"] = recall_line(validate_reference(rd, known_all, margin))
            row["Crupi unknown"] = recall_line(validate_reference(rd, unknown_all, margin))
        sens.append(row)
    pd.DataFrame(sens).to_csv(out / "sensitivity.csv", index=False)

    s = cat_stats["stats"]
    summary = {
        "generated": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "validation_git_commit": git_commit(),
        "versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "run": str(run.relative_to(BASE_DIR)),
        "period": {"start_date": start_date, "end_date": end_date},
        "days": len(window_days(start_date, end_date)),
        "data_days": len(rd.data_days),
        "match_margin_s": PRIMARY_MARGIN,
        "events": {"total": len(ev), "CE": {c: int((ev["CE"] == c).sum()) for c in "RSP"},
                   "match_gbm": int(ev["match_gbm"].sum()), "match_crupi_known": int(ev["match_crupi_known"].sum()),
                   "match_crupi_unknown": int(ev["match_crupi_unknown"].sum()), "without_counterpart": len(lonely)},
        "gbm": s,
        "flags": {"zero_prediction_bins": int(len(rd.zero_rows)),
                  "near_zero_events": [int(t) for t in ev.loc[ev["near_zero_prediction"], "trig_ids"]],
                  "short_unmasked_passages": None},
        "crupi": None,
        "classification": None,
    }

    # SAA passages not covered by the mask
    lo = (pd.Timestamp(start_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    hi = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    track = PoshistTrack.for_days(poshist_dir, window_days(lo, hi))
    summary["flags"]["short_unmasked_passages"] = int(len(unmasked_passages(track.passages(), rd.met)))

    if with_crupi:
        k_rs, u_rs = known[known["CE"].isin(["R", "S"])], unknown[unknown["CE"].isin(["R", "S"])]
        summary["crupi"] = {
            "known": {"in_window": len(known), "total": len(known_all), "matched": int(known["matched"].sum()),
                      "by_tier": {c: [int(known.loc[known["CE"] == c, "matched"].sum()), int((known["CE"] == c).sum())] for c in "RSP"}},
            "unknown": {"in_window": len(unknown), "total": len(unknown_all), "matched": int(unknown["matched"].sum()),
                        "by_tier": {c: [int(unknown.loc[unknown["CE"] == c, "matched"].sum()), int((unknown["CE"] == c).sum())] for c in "RSP"}},
            "known_RS": [int(k_rs["matched"].sum()), len(k_rs)],
            "unknown_RS": [int(u_rs["matched"].sum()), len(u_rs)],
            "paper": PAPER,
        }
        significance_vs_crupi(known, unknown).to_csv(out / "significance_vs_crupi.csv", index=False)
        cl = classification_tables(rd, known, unknown)
        if cl is not None:
            cl["table"].to_csv(out / "classification_vs_crupi.csv", index=False)
            cl["rules"].to_csv(out / "classification_rules.csv", index=False)
            cl["confusion"].to_csv(out / "classification_confusion.csv")
            summary["classification"] = {"matched": cl["n"], "correct": cl["correct"], "single_label": cl["single"]}

    this_bundle = run_model_bundle(run)
    summary["model_bundle"] = this_bundle
    summary["model_description"] = model_description(this_bundle)

    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return summary


def main() -> None:
    from connections.utils.config import DATA_DIR, FOLD_POSHIST
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="run folder data/runs/<start>_<end>/engine-v<N>[-<label>]")
    args = parser.parse_args()
    setup_logging()
    s = validate_run(args.run, DATA_DIR / FOLD_POSHIST)
    detail(f"validation written to {Path(args.run) / VALIDATION_DIR}: {s['events']['total']} events, "
           f"GBM {s['gbm']['detected']}/{s['gbm']['available']}")


if __name__ == "__main__":
    main()
