"""
Deterministic validation of one engine run against

  A. the official Fermi/GBM trigger catalog (and the Burst Catalog for GRB T90), and
  B. the tables of Crupi et al. (known: Table 11, unknown: Table 10),

with one-to-one matching (benchmark/matching.py). Every number in the report is
computed here from files on disk.

Usage (from repo root):
    python -m benchmark.validate [--run data/runs/<start>_<end>/engine-v<N>] [--out benchmark/out]

Outputs in --out: REPORT.md and CSV tables (matches_*.csv, events_without_counterpart.csv,
sensitivity.csv, classification_*.csv when a classified table exists).
"""

import argparse
import json
import platform
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from benchmark.matching import BINLENGTH, PRIMARY_MARGIN, match_one_to_one
from connections.utils.config import BASE_DIR, DATA_DIR, END_DATE, FOLD_POSHIST, GBM_BURST_DB, GBM_TRIG_DB, START_DATE, run_dir
from models.saa_flags import EDGE_WINDOW_S, REGION_DEG, SAA_GAP_S, PoshistTrack, compute_saa_flags
from utils.fermi_time import utc_to_met
from utils.keys import get_keys
from utils.period import days_with_data, in_window, window_days

REF_DIR = BASE_DIR / "benchmark" / "reference"
SAA_GAP_S = 500.0
SAA_GUARD_S = 150.0
SENSITIVITY_MARGINS = {"primary (2 bins)": PRIMARY_MARGIN, "10 s": 10.0, "60 s": 60.0, "1200 s": 1200.0}
PAPER = {  # Crupi et al. 2023, 2019 period to 2019-07-09 (docs/WORKING_RULES.md §3)
    "grb_burst_catalog": 96, "grb_missing": 15, "grb_detected": 65, "grb_available": 81,
    "long_detected": 60, "long_available": 68, "short_detected": 5, "short_available": 13,
    "events_total": 100,
}
SECTION_1_TIMES = ["2019-03-08 22:10:12", "2019-05-25 00:45:54"]


# ----------------------------------------------------------------------------- loading
class RunData:
    def __init__(self, run: Path):
        self.run = run
        keys = get_keys()
        frg = pd.read_csv(run / "pred" / "frg.csv", usecols=["met", "timestamp"])
        bkg = pd.read_csv(run / "pred" / "bkg.csv", usecols=keys)
        self.met = frg["met"].to_numpy(dtype=float)
        self.timestamp = frg["timestamp"]
        self.valid = np.isfinite(bkg.to_numpy(dtype=float)).any(axis=1)
        focus = pd.read_csv(run / "trig" / "trig.csv", usecols=get_keys(rs=["1"]))
        self.focus_r1_max = focus.max(axis=1, skipna=True).to_numpy(dtype=float)
        self.order = np.argsort(self.met, kind="stable")
        self.met_sorted = self.met[self.order]
        gaps = np.where(np.diff(self.met) > SAA_GAP_S)[0]
        self.gap_edges = np.sort(np.concatenate([self.met[gaps], self.met[gaps + 1]]))
        self.data_days = days_with_data(self.timestamp, START_DATE, END_DATE)

        self.events = pd.read_csv(run / "results" / "events_table.csv")
        # 4 timestamps repeat at day boundaries (overlapping CSPEC files): keep the first occurrence
        ts_to_met = pd.Series(self.met, index=self.timestamp.values)
        ts_to_met = ts_to_met[~ts_to_met.index.duplicated(keep="first")]
        self.events["t_start"] = self.events["start_times_offset"].map(ts_to_met).fillna(self.events["start_met"])
        self.events["t_end"] = self.events["end_met"]
        self.manifest = json.loads((run / "manifest.json").read_text()) if (run / "manifest.json").exists() else {}

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
    cat = cat[in_window(cat["trigger_time"], START_DATE, END_DATE)].copy()
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


def load_reference(kind: str, rd: RunData) -> pd.DataFrame:
    ref = pd.read_csv(REF_DIR / f"crupi_2019_{kind}.csv")
    ref["in_window"] = in_window(ref["trigger_time_utc"], START_DATE, END_DATE).to_numpy()
    ref["t"] = utc_to_met(ref["trigger_time_utc"])
    ref["has_data"] = [rd.has_data(t) for t in ref["t"]]
    return ref


def s_value(v) -> float:
    s = str(v).strip()
    return 10.0 if s == ">10" else float(s)


# ----------------------------------------------------------------------------- validation
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
    if np.isfinite(f) and f <= 3.0:
        return f"below threshold: max FOCuS r1 within ±60 s = {f:.2f} sigma"
    if np.isfinite(f):
        return f"FOCuS r1 reaches {f:.2f} sigma within ±60 s but no event covers the time (nearest event start {row['nearest_event_dt_s']:+.0f} s)"
    return "no FOCuS value nearby"


# ----------------------------------------------------------------------------- report helpers
def md_table(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    if df.empty:
        return "_(nessuna riga)_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else format(v, floatfmt))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


RULE_CLASSES = ["GRB", "SF", "TGF", "UNC(LP)", "GF"]


def classification_section(rd: RunData, known: pd.DataFrame, unknown: pd.DataFrame, out: Path) -> List[str]:
    path = rd.run / "results" / "events_classified.csv"
    intro = [
        "Il classificatore è la **baseline euristica** di Crupi, da superare con un modello appreso (XGBoost, fase successiva). "
        "Le regole vengono dalla \"manual classification logic\" di `pipeline/script_classification2.py` (upstream, 2023): "
        "soglie lette da decision tree uno-contro-resto (profondità 3) e rifinite a mano sul catalogo etichettato 2010-11, 2014, 2019; "
        "le random forest servivano allo studio delle feature, non come classificatore finale.",
        "",
        "Differenze rispetto alle regole originali: mancano la regola FP e le feature `fe_*` della curva di luce (calcolate con `tsfel` "
        "nel branch upstream `ric_review_28062023`), quindi i termini `fe_wet > 2.054` (GRB) e `fe_skw <= 0.345` (UNC(LP)) sono neutri. "
        "Le regole sono valutate solo sugli eventi abbinati a Crupi (gli eventi senza controparte non hanno una classe di riferimento).",
        "",
    ]
    if not path.exists():
        return intro + ["_Tabella classificata assente (`events_classified.csv`): eseguire `python -m benchmark.classify`._"]
    cls = pd.read_csv(path).set_index("trig_ids")
    rows = []
    for kind, ref in (("noti", known), ("inediti", unknown)):
        for _, r in ref[ref["matched"]].iterrows():
            tid = rd.events.at[r["event"], "trig_ids"]
            row = {"set": kind, "id": r["id"], "crupi_class": "/".join(sorted(crupi_class(r["catalog_name"]))),
                   "predicted_class": cls.at[tid, "predicted_class"]}
            for c in RULE_CLASSES:
                row[f"rule_{c}"] = bool(cls.at[tid, f"rule_{c}"]) if f"rule_{c}" in cls.columns else np.nan
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out / "classification_vs_crupi.csv", index=False)
    if df.empty:
        return intro + ["_Nessun evento abbinato da classificare._"]

    truth = df["crupi_class"].str.split("/")
    ovr = []
    for c in RULE_CLASSES:
        if f"rule_{c}" not in df.columns:
            continue
        t = truth.apply(lambda s: c in s)
        pr = df[f"rule_{c}"].astype(bool)
        tp, fp, fn = int((t & pr).sum()), int((~t & pr).sum()), int((t & ~pr).sum())
        ovr.append({"regola": c, "positivi Crupi": int(t.sum()), "flag regola": int(pr.sum()), "TP": tp, "FP": fp, "FN": fn,
                    "precision": tp / (tp + fp) if tp + fp else np.nan, "recall": tp / (tp + fn) if tp + fn else np.nan})

    single = df[~df["crupi_class"].str.contains("/")]
    labels = sorted(set(single["crupi_class"]) | set(single["predicted_class"]))
    cm = pd.crosstab(pd.Categorical(single["crupi_class"], categories=labels),
                     pd.Categorical(single["predicted_class"], categories=labels), dropna=False)
    cm.index.name, cm.columns.name = "Crupi", "predetta"
    correct = df.apply(lambda r: r["predicted_class"] in r["crupi_class"].split("/"), axis=1)
    return intro + [
        f"### Per regola, uno-contro-resto (come nello script di Crupi) — {len(df)} eventi abbinati",
        "",
        md_table(pd.DataFrame(ovr)),
        "",
        "### Etichetta singola (nostra convenzione di priorità: GRB, TGF, SF, UNC(LP), GF, UNC)",
        "",
        f"Classe predetta tra quelle tentative di Crupi: {int(correct.sum())}/{len(df)} ({100 * correct.mean():.1f}%).",
        "",
        f"Matrice di confusione sugli eventi con classe Crupi univoca ({len(single)}):",
        "",
        "```",
        cm.to_string(),
        "```",
        "",
        "Leakage: `tests/test_classifier.py::test_catalog_does_not_change_prediction` verifica che le colonne del catalogo non cambino "
        "la classe; `TestRulesMatchCrupi` verifica che i flag coincidano con la trascrizione delle regole di Crupi.",
    ]


def crupi_class(name: str) -> set:
    s = str(name)
    if s.startswith("UNKNOWN:"):
        return set(s.split(":", 1)[1].strip().split("/"))
    for prefix, label in (("GRB", "GRB"), ("SFL", "SF"), ("TGF", "TGF"), ("LOCLPAR", "UNC(LP)"), ("TRANSNT", "UNC"), ("UNCERT", "UNC"), ("SGR", "UNC")):
        if s.startswith(prefix):
            return {label}
    return {"UNC"}


# ----------------------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=run_dir())
    parser.add_argument("--out", type=Path, default=BASE_DIR / "benchmark" / "out")
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    args.run = args.run.resolve()
    rd = RunData(args.run)
    ev = rd.events
    cat = load_trigger_catalog(rd)
    grb = load_burst_catalog()
    known_all, unknown_all = load_reference("known", rd), load_reference("unknown", rd)

    # ---- primary matching
    cat_m, cat_stats = validate_catalog(rd, cat, grb, PRIMARY_MARGIN)
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
    cat_m.to_csv(out / "matches_gbm_catalog.csv", index=False)
    known.to_csv(out / "matches_crupi_known.csv", index=False)
    unknown.to_csv(out / "matches_crupi_unknown.csv", index=False)

    ev_gbm = set(cat_m.loc[cat_m["matched"], "event"])
    ev_known = set(known.loc[known["matched"], "event"])
    ev_unknown = set(unknown.loc[unknown["matched"], "event"])
    ev = ev.copy()
    ev["match_gbm"] = ev.index.isin(ev_gbm)
    ev["match_crupi_known"] = ev.index.isin(ev_known)
    ev["match_crupi_unknown"] = ev.index.isin(ev_unknown)
    ev["counterpart"] = ev["match_gbm"] | ev["match_crupi_known"] | ev["match_crupi_unknown"]

    # ---- post-processing SAA flags (columns only: the event list does not change)
    days = window_days((pd.Timestamp(START_DATE) - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                       (pd.Timestamp(END_DATE) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    flags = compute_saa_flags(ev["t_start"].to_numpy(), PoshistTrack.for_days(DATA_DIR / FOLD_POSHIST, days), rd.met)
    flags.index = ev.index
    ev = pd.concat([ev, flags], axis=1)
    ev[["trig_ids", "start_times", "duration", "detectors", "sigma_C", "CE", "counterpart", "match_gbm",
        "match_crupi_known", "match_crupi_unknown"] + list(flags.columns)].to_csv(out / "events_flags.csv", index=False)
    flag_rows = []
    for label, sub in (("abbinati Crupi/GBM", ev[ev["counterpart"]]), ("senza controparte", ev[~ev["counterpart"]]), ("tutti", ev)):
        flag_rows.append({"eventi": label, "n": len(sub),
                          "saa_edge_short_passage": int(sub["saa_edge_short_passage"].sum()),
                          "saa_region_proximity": int(sub["saa_region_proximity"].sum()),
                          "almeno uno": int((sub["saa_edge_short_passage"] | sub["saa_region_proximity"]).sum())})
    flag_table = pd.DataFrame(flag_rows)

    lonely = ev[~(ev["match_gbm"] | ev["match_crupi_known"] | ev["match_crupi_unknown"])].copy()
    # per-event diagnosis: SAA proximity, nearest Crupi reference, orbit, class (if available)
    ref_t = np.concatenate([known_all["t"].to_numpy(), unknown_all["t"].to_numpy()])
    ref_id = np.concatenate([known_all["id"].to_numpy(), unknown_all["id"].to_numpy()])
    edges = rd.gap_edges
    lonely["dist_saa_gap_s"] = [float(np.min(np.abs(edges - t))) if len(edges) else np.nan for t in lonely["t_start"]]
    nearest = [int(np.argmin(np.abs(ref_t - t))) for t in lonely["t_start"]]
    lonely["nearest_crupi"] = [ref_id[i] for i in nearest]
    lonely["nearest_crupi_dt_h"] = [(ref_t[i] - t) / 3600 for i, t in zip(nearest, lonely["t_start"])]
    cls_path = rd.run / "results" / "events_classified.csv"
    extra = ["l", "lat_fermi", "lon_fermi", "predicted_class"]
    if cls_path.exists():
        lonely = lonely.merge(pd.read_csv(cls_path)[["trig_ids"] + extra], on="trig_ids", how="left")
    lonely_cols = ["trig_ids", "start_times", "duration", "detectors", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE",
                   "catalog_triggers", "dist_saa_gap_s", "nearest_crupi", "nearest_crupi_dt_h",
                   "saa_edge_short_passage", "saa_region_proximity"] + [c for c in extra if c in lonely.columns]
    lonely[lonely_cols].to_csv(out / "events_without_counterpart.csv", index=False)

    # ---- sensitivity
    sens = []
    for label, margin in SENSITIVITY_MARGINS.items():
        _, cs = validate_catalog(rd, cat, grb, margin)
        k = validate_reference(rd, known_all, margin)
        u = validate_reference(rd, unknown_all, margin)
        sens.append({"margine": label, "GBM rivelati/disponibili": f"{cs['stats']['detected']}/{cs['stats']['available']}",
                     "GRB": f"{cs['stats']['grb_detected']}/{cs['stats']['grb_available']}",
                     "Crupi noti": recall_line(k), "Crupi inediti": recall_line(u)})
    sens = pd.DataFrame(sens)
    sens.to_csv(out / "sensitivity.csv", index=False)

    # ---- S comparison with Crupi (matched events with numeric reference S)
    both = pd.concat([known[known["matched"]], unknown[unknown["matched"]]])
    s_rows = []
    for rng in ("r0", "r1", "r2"):
        ref_s = both[f"S_{rng}"].astype(str).str.strip()
        sel = (ref_s != ">10") & (ref_s.astype(str) != "0") & (ref_s != "0.0")
        sel &= both[f"our_S_{rng}"] > 0
        ratio = both.loc[sel, f"our_S_{rng}"] / ref_s[sel].astype(float)
        s_rows.append({"banda": rng, "eventi": int(sel.sum()), "mediana S_nostro/S_Crupi": ratio.median() if len(ratio) else np.nan,
                       "16° pct": ratio.quantile(0.16) if len(ratio) else np.nan, "84° pct": ratio.quantile(0.84) if len(ratio) else np.nan})
    s_cmp = pd.DataFrame(s_rows)

    # ---- section 1 cases
    sec1 = []
    for t_utc in SECTION_1_TIMES:
        t = utc_to_met([t_utc])[0]
        near = ev[(ev["t_start"] - 60 <= t) & (t <= ev["t_end"] + 60)]
        cat_near = cat_m[np.abs(cat_m["trig_met"] - t) <= 300]
        for _, c in cat_near.iterrows():
            sec1.append({"tempo (§1)": t_utc, "trigger GBM": c["name"], "trigger_time": c["trigger_time"],
                         "rivelato (regola primaria)": bool(c["matched"]),
                         "evento": int(ev.at[c["event"], "trig_ids"]) if c["matched"] else "",
                         "inizio evento - trigger [s]": -c["dt_start_s"] if c["matched"] else np.nan,
                         "eventi nostri entro ±60 s": len(near),
                         "in tabelle Crupi": bool((np.abs(known_all["t"] - t) <= 600).any() or (np.abs(unknown_all["t"] - t) <= 600).any())})
    sec1 = pd.DataFrame(sec1)

    # ---- acceptance
    s = cat_stats["stats"]
    k_rs = known[known["CE"].isin(["R", "S"])]
    u_rs = unknown[unknown["CE"].isin(["R", "S"])]
    acc = [
        ("Noti di Crupi ritrovati ≥ 90% (≥ 64/71)", recall_line(known), known["matched"].mean() >= 0.9),
        ("Tutti gli R e S noti ritrovati (65)", recall_line(k_rs), bool(k_rs["matched"].all())),
        ("Inediti R+S ritrovati ≥ 90% (≥ 15/16)", recall_line(u_rs), u_rs["matched"].mean() >= 0.9 if len(u_rs) else False),
        ("Inediti complessivi ≥ 70% (≥ 17/24)", recall_line(unknown), unknown["matched"].mean() >= 0.7),
        ("Recall GRB T90 > 4.096 s ~ 88%", f"{s['long_detected']}/{s['long_available']}", None),
        ("Recall GRB T90 ≤ 4.096 s ~ 34%", f"{s['short_detected']}/{s['short_available']}", None),
        ("Numero eventi ~ 100 ± qualche decina", str(len(ev)), 60 <= len(ev) <= 140),
    ]
    acc_df = pd.DataFrame([{"criterio": a, "misurato": b, "esito": "n/a (ordine di grandezza)" if c is None else ("OK" if c else "NON RAGGIUNTO")} for a, b, c in acc])

    # ---- report
    unm_cols = ["id", "trigger_time_utc", "detectors", "catalog_name", "S_r1", "CE", "has_data", "focus_r1_max_pm60s", "nearest_event_dt_s", "diagnosis"]
    man = rd.manifest
    last_run = man.get("runs", [{}])[-1]
    lines = [
        "# Validazione baseline 2019",
        "",
        f"Generato da `python -m benchmark.validate` il {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}. Tutte le cifre sono calcolate da file su disco.",
        "",
        "## Contesto",
        "",
        f"- Periodo: {START_DATE} → {END_DATE} (inclusivo); giorni con dati: {len(rd.data_days)}.",
        f"- Run: `{args.run.relative_to(BASE_DIR)}`; motore prodotto dal commit `{last_run.get('git_commit', '?')}` (codice modificato: {last_run.get('code_dirty', '?')}).",
        f"- Validazione eseguita dal commit `{git_commit()}`; Python {platform.python_version()}, pandas {pd.__version__}, numpy {np.__version__}.",
        f"- Modello: `{man.get('parameters', {}).get('model_bundle', '?')}`; seed di training {man.get('parameters', {}).get('train_seed', '?')} (modello legacy: addestrato una volta, seed non registrato).",
        f"- Parametri del motore: soglia {man.get('parameters', {}).get('trigger', {}).get('threshold_sigma')} σ in r1, mu_min {man.get('parameters', {}).get('focus', {}).get('mu_min')}, t_max {man.get('parameters', {}).get('focus', {}).get('t_max_bins')} bin, esclusione SAA ±{man.get('parameters', {}).get('saa_exclusion_bins_each_side')} bin, merge {man.get('parameters', {}).get('merge_s')} s.",
        f"- Matching: uno-a-uno; un riferimento è abbinato se il suo istante cade in [inizio evento − {PRIMARY_MARGIN:.3f} s, fine evento + {PRIMARY_MARGIN:.3f} s]; l'inizio evento è il change point FOCuS (`start_times_offset`).",
        "",
        "## Criteri di accettazione (docs/WORKING_RULES.md §6, finestra al 30 giugno)",
        "",
        md_table(acc_df),
        "",
        "## Eventi della pipeline",
        "",
        f"- Totale: **{len(ev)}**; tier CE: {ev['CE'].value_counts().reindex(['R', 'S', 'P']).fillna(0).astype(int).to_dict()}.",
        f"- Abbinati al catalogo trigger GBM: {int(ev['match_gbm'].sum())}; a Crupi noti: {int(ev['match_crupi_known'].sum())}; a Crupi inediti: {int(ev['match_crupi_unknown'].sum())}.",
        f"- Senza controparte (né GBM né Crupi): **{len(lonely)}** ({len(lonely) / max(len(rd.data_days), 1):.2f} al giorno su {len(rd.data_days)} giorni con dati). Non sono \"scoperte\": vedi `events_without_counterpart.csv`.",
        f"- Riferimento paper (fino al 9 luglio): {PAPER['events_total']} eventi (74 noti, 25 incerti, 1 falso).",
        "",
        "### Diagnosi per evento degli eventi senza controparte",
        "",
        (f"Distanza dal buco SAA più vicino: minima {lonely['dist_saa_gap_s'].min():.0f} s, mediana {lonely['dist_saa_gap_s'].median():.0f} s. "
         f"Riferimento di Crupi più vicino entro 1 h: {int((lonely['nearest_crupi_dt_h'].abs() < 1).sum())}/{len(lonely)}. "
         f"Tier: {lonely['CE'].value_counts().reindex(['R', 'S', 'P']).fillna(0).astype(int).to_dict()}; "
         f"con il rivelatore nb: {int(lonely['detectors'].str.contains('nb').sum())}/{len(lonely)} "
         f"(contro {int(ev.loc[ev['match_crupi_known'] | ev['match_crupi_unknown'], 'detectors'].str.contains('nb').sum())}/"
         f"{int((ev['match_crupi_known'] | ev['match_crupi_unknown']).sum())} negli eventi abbinati a Crupi)."),
        "",
        md_table(lonely[[c for c in ["trig_ids", "start_times", "duration", "detectors", "sigma_C", "CE", "dist_saa_gap_s",
                                     "nearest_crupi", "nearest_crupi_dt_h", "saa_edge_short_passage", "saa_region_proximity",
                                     "l", "lat_fermi", "predicted_class"] if c in lonely.columns]]),
        "",
        "### Flag SAA di post-processing (non cambiano l'elenco degli eventi)",
        "",
        f"`saa_edge_short_passage`: inizio evento (change point) entro {EDGE_WINDOW_S:.0f} s prima dell'entrata o dopo l'uscita di un "
        f"passaggio SAA il cui buco nei dati è ≤ {SAA_GAP_S:.0f} s, quindi non mascherato. `saa_region_proximity`: Fermi entro "
        f"{REGION_DEG}° dalla regione con flag SAA nelle POSHIST. Definizioni in `models/saa_flags.py` e `docs/ORBIT_ANALYSIS.md`; "
        "per evento in `events_flags.csv`.",
        "",
        md_table(flag_table),
        "",
        "## A. Catalogo trigger GBM",
        "",
        f"- Trigger nel periodo, nei giorni con dati: {s['catalog_triggers']}; senza dati validi all'istante del trigger (maschera SAA/buchi): {s['missing_no_data']}; disponibili: {s['available']}; rivelati: **{s['detected']}**.",
        f"- Con la definizione di docs/WORKING_RULES.md (entro ±150 s da un buco > 500 s): {s['near_saa_150s']} trigger.",
        "",
        md_table(cat_stats["by_type"].reset_index()[["trigger_type", "total_in_window", "missing_no_data", "available", "detected"]]),
        "",
        "GRB del Burst Catalog:",
        "",
        md_table(pd.DataFrame([
            {"": "GRB nel periodo", "nostro (al 30/06)": s["grb_total"], "paper (al 9/07)": PAPER["grb_burst_catalog"]},
            {"": "senza dati (SAA)", "nostro (al 30/06)": s["grb_missing"], "paper (al 9/07)": PAPER["grb_missing"]},
            {"": "rivelati / disponibili", "nostro (al 30/06)": f"{s['grb_detected']}/{s['grb_available']}", "paper (al 9/07)": f"{PAPER['grb_detected']}/{PAPER['grb_available']}"},
            {"": "T90 > 4.096 s", "nostro (al 30/06)": f"{s['long_detected']}/{s['long_available']}", "paper (al 9/07)": f"{PAPER['long_detected']}/{PAPER['long_available']} (88%)"},
            {"": "T90 ≤ 4.096 s", "nostro (al 30/06)": f"{s['short_detected']}/{s['short_available']}", "paper (al 9/07)": f"{PAPER['short_detected']}/{PAPER['short_available']} (34%)"},
        ])),
        "",
        "## B. Tabelle di Crupi",
        "",
        f"- Noti (Tabella 11, in finestra {len(known)} di {len(known_all)}): ritrovati **{recall_line(known)}**; per tier: "
        + ", ".join(f"{c} {recall_line(known[known['CE'] == c])}" for c in ("R", "S", "P")) + ".",
        f"- Inediti (Tabella 10, in finestra {len(unknown)} di {len(unknown_all)}): ritrovati **{recall_line(unknown)}**; per tier: "
        + ", ".join(f"{c} {recall_line(unknown[unknown['CE'] == c])}" for c in ("R", "S", "P")) + ".",
        "",
        "### Noti non ritrovati",
        "",
        md_table(known.loc[~known["matched"], unm_cols]),
        "",
        "### Inediti non ritrovati",
        "",
        md_table(unknown.loc[~unknown["matched"], unm_cols]),
        "",
        "### Significatività: nostro S rispetto a quello di Crupi (eventi abbinati, S di riferimento numerico)",
        "",
        md_table(s_cmp),
        "",
        "## Sensibilità alla regola di matching",
        "",
        md_table(sens),
        "",
        "## Casi del §1 di docs/WORKING_RULES.md",
        "",
        md_table(sec1),
        "",
        "## Classificazione (Fase 4)",
        "",
        *classification_section(rd, known, unknown, out),
        "",
        "## Limiti noti",
        "",
        "- Stabilità rispetto al seed di training non misurata (richiede un nuovo training: da confermare).",
        "- Classificatore: mancano la regola FP e le feature `fe_*` (tsfel, branch upstream `ric_review_28062023`): i termini che le usano sono neutri.",
        "- Il paper conta fino al 9 luglio; i numeri del paper sono confronti di ordine di grandezza.",
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
