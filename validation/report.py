"""
Readable report of a run (pipeline step 9), written only from files on disk:
<run>/RESULTS.md, with the same sections for every run (a section without inputs says so).

Inputs: <run>/manifest.json, the bundle metadata, <run>/results/*.csv and <run>/validation/
(validation/validate.py). No number is written by hand. The derived tables of sections 6 and 9
are also written as CSV in <run>/validation/.

Usage (repo root):
    python -m validation.report --run data/runs/<start>_<end>/engine-v<N>[-<label>]
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from connections.utils.config import (BASE_DIR, BIN_LENGTH_S, CRUPI_REFERENCE_PERIOD, FOCUS_T_MAX_BINS, MATCH_MARGIN_S,
                                      run_period)
from utils.logs import detail, setup_logging
from utils.run_options import bundle_seed, manifest_model, read_manifest
from validation.report_tables import (TYPE_TO_CLASS, JoinError, check_gbm_join, confusion_metrics, crupi_named_list,
                                      gbm_named_list, gbm_type_vs_class)

OK, KO = "✔", "✘"
RESULTS_FILE = "RESULTS.md"
NOT_RUN = "_Validation (step 8) not run._"


# ----------------------------------------------------------------------------- markdown helpers
def md_table(df: pd.DataFrame, floatfmt: str = ".2f", index: bool = False) -> str:
    """Markdown table without external dependencies."""
    if index:
        df = df.reset_index()
    if df.empty:
        return "_(no rows)_"
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


def read_csv(path: Path, **kw) -> Optional[pd.DataFrame]:
    return pd.read_csv(path, **kw) if path.exists() else None


def ratio(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else "0/0"


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def pct_table(df: pd.DataFrame) -> pd.DataFrame:
    """Percentages as text with one decimal ('—' where undefined)."""
    return df.apply(lambda col: col.map(lambda v: "—" if pd.isna(v) else f"{v:.1f}%"))


# ----------------------------------------------------------------------------- run facts
def run_facts(run: Path) -> dict:
    """Facts used by the report, from manifest, bundle metadata and outputs."""
    run = Path(run)
    man = read_manifest(run)
    model = manifest_model(man)
    bundle = model.get("bundle")
    bundle_path = BASE_DIR / bundle if bundle else None
    meta_path = bundle_path / "metadata.json" if bundle_path else None
    meta = json.loads(meta_path.read_text()) if meta_path and meta_path.exists() else {}
    seed = model.get("seed", bundle_seed(bundle_path) if bundle_path else None)
    start, end = run_period(run)
    summary_path = run / "validation" / "summary.json"
    return {
        "run": run, "name": run.name, "start": start, "end": end, "manifest": man, "model": model,
        "bundle": bundle, "meta": meta, "seed": seed,
        "events": read_csv(run / "results" / "events_table.csv"),
        "summary": json.loads(summary_path.read_text()) if summary_path.exists() else None,
        "classified": read_csv(run / "results" / "events_classified.csv"),
        "localized": (run / "results" / "events_table_loc.csv").exists(),
    }


# ----------------------------------------------------------------------------- sections
def section_run(f: dict) -> List[str]:
    man, model, meta = f["manifest"], f["model"], f["meta"]
    p = man.get("parameters", {})
    history = man.get("runs", [])
    reused = man.get("reused_from")
    lines = [
        "## 1. Run, network and parameters",
        "",
        f"- Period: **{f['start']} → {f['end']}** (UTC days, both included); run `{rel(f['run'])}`.",
        f"- Engine: v{p.get('engine_version', '?')}; executions: "
        + "; ".join(f"{h.get('started', '?')[:16].replace('T', ' ')} commit `{h.get('git_commit', '?')[:10]}`"
                    + (f" (steps to run at start: {', '.join(map(str, h['steps']))})" if h.get("steps") else "")
                    + (" (modified code)" if h.get("code_dirty") else "") for h in history)
        + ".",
        f"- Network: bundle `{f['bundle'] or '?'}`; training seed {f['seed'] if f['seed'] is not None else 'not recorded'}; "
        f"bundle sha256 `{model.get('checksum', 'not recorded')}`.",
    ]
    if reused:
        lines.append(f"- Predictions (step 3) and FOCuS outputs (step 4) computed with the same bundle by engine "
                     f"v{reused['engine_version']}, whose steps 3-4 are unchanged; linked from `{reused['run']}` ({reused['how']}).")
    if meta.get("source") == "trained":
        h = meta.get("hyperparameters", {})
        lines.append(f"- Training: {meta.get('epochs_run', '?')} epochs (best {meta.get('best_epoch', '?')}), "
                     f"{h.get('units', '?')} units, lr {h.get('lr', '?')}, batch {h.get('batch_size', '?')}, "
                     f"{meta.get('training_seconds', '?')} s on {', '.join(meta.get('devices', [])) or '?'}.")
    focus, trig = p.get("focus", {}), p.get("trigger", {})
    lines += [
        f"- Parameters: bin {p.get('bin_length_s')} s; FOCuS mu_min {focus.get('mu_min')}, t_max {focus.get('t_max_bins')} bins "
        f"(input: {focus.get('input')}); threshold {trig.get('threshold_sigma')} σ in {trig.get('range')} on ≥ "
        f"{trig.get('min_detectors')} detector(s); merge {p.get('merge_s')} s; SAA mask ±{p.get('saa_exclusion_bins_each_side')} "
        f"bins around data gaps > {p.get('saa_gap_s')} s.",
        "",
    ]
    return lines


def section_events(f: dict) -> List[str]:
    ev, s = f["events"], f["summary"]
    lines = ["## 2. Events", ""]
    if ev is None:
        return lines + ["_Step 5 not run: `results/events_table.csv` missing._", ""]
    ce = {c: int((ev["CE"] == c).sum()) for c in "RSP"}
    lines.append(f"- Total: **{len(ev)}**; CE tiers: R {ce['R']}, S {ce['S']}, P {ce['P']} "
                 "(R: several detectors and several energy ranges; S: several detectors, one range; P: the others).")
    if s:
        e = s["events"]
        lines.append(f"- Matched to the GBM trigger catalog: {e['match_gbm']}"
                     + (f"; to Crupi's known events: {e['match_crupi_known']}; to Crupi's unknown events: {e['match_crupi_unknown']}"
                        if s["crupi"] else "")
                     + f". Without counterpart: **{e['without_counterpart']}** "
                     f"({e['without_counterpart'] / max(s['data_days'], 1):.2f} per day over {s['data_days']} days with data).")
    return lines + [""]


def section_gbm(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 3. Official Fermi-GBM catalog", ""]
    if not s:
        return lines + [NOT_RUN, ""]
    g = s["gbm"]
    lines += [
        f"Primary rule: one-to-one matching, trigger time within [event start − {s['match_margin_s']:.3f} s, "
        f"event end + {s['match_margin_s']:.3f} s].",
        "",
        f"- Triggers in the period, on days with data: {g['catalog_triggers']}; without valid data at the trigger time "
        f"(SAA mask or gap): {g['missing_no_data']}; available: {g['available']}; detected: **{g['detected']}**.",
        f"- Within ±150 s of a data gap > 500 s: {g['near_saa_150s']} triggers.",
        "",
        md_table(pd.read_csv(v / "gbm_by_type.csv")),
        "",
        "GRBs of the Burst Catalog (T90):",
        "",
    ]
    rows = [{"": "GRBs in the period", "this run": g["grb_total"]},
            {"": "without data (SAA)", "this run": g["grb_missing"]},
            {"": "detected / available", "this run": ratio(g["grb_detected"], g["grb_available"])},
            {"": "T90 > 4.096 s", "this run": ratio(g["long_detected"], g["long_available"])},
            {"": "T90 ≤ 4.096 s", "this run": ratio(g["short_detected"], g["short_available"])}]
    table = pd.DataFrame(rows)
    if s["crupi"]:
        P = s["crupi"]["paper"]
        table["paper (to 2019-07-09)"] = [P["grb_burst_catalog"], P["grb_missing"], f"{P['grb_detected']}/{P['grb_available']}",
                                          f"{P['long_detected']}/{P['long_available']} (88%)",
                                          f"{P['short_detected']}/{P['short_available']} (34%)"]
    lines += [md_table(table), "", "Sensitivity to the matching window:", "", md_table(pd.read_csv(v / "sensitivity.csv")), ""]
    return lines


def acceptance_rows(s: dict) -> pd.DataFrame:
    c, g = s["crupi"], s["gbm"]
    kn, un = c["known"], c["unknown"]
    rs_k, rs_u = c["known_RS"], c["unknown_RS"]
    rows = [
        ("Crupi's known events found ≥ 90%", ratio(kn["matched"], kn["in_window"]),
         kn["in_window"] and kn["matched"] / kn["in_window"] >= 0.9),
        ("All known R and S events found", ratio(*rs_k), rs_k[0] == rs_k[1]),
        ("Unknown R+S events found ≥ 90%", ratio(*rs_u), bool(rs_u[1]) and rs_u[0] / rs_u[1] >= 0.9),
        ("All unknown events found ≥ 70%", ratio(un["matched"], un["in_window"]),
         un["in_window"] and un["matched"] / un["in_window"] >= 0.7),
    ]
    out = [{"criterion (docs/VALIDATION.md)": a, "measured": b, "result": OK if ok else KO} for a, b, ok in rows]
    out += [
        {"criterion (docs/VALIDATION.md)": "GRB recall T90 > 4.096 s ~ 88% (paper)",
         "measured": ratio(g["long_detected"], g["long_available"]), "result": "order of magnitude"},
        {"criterion (docs/VALIDATION.md)": "GRB recall T90 ≤ 4.096 s ~ 34% (paper)",
         "measured": ratio(g["short_detected"], g["short_available"]), "result": "order of magnitude"},
        {"criterion (docs/VALIDATION.md)": "Number of events ~ 100 (paper, to 2019-07-09)",
         "measured": str(s["events"]["total"]), "result": "informative: depends on the network"},
    ]
    return pd.DataFrame(out)


def section_crupi(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 4. Comparison with Crupi et al. (2023)", ""]
    if not s:
        return lines + [NOT_RUN, ""]
    if not s["crupi"]:
        return lines + [f"_Not applicable: Crupi's tables cover only {CRUPI_REFERENCE_PERIOD[0]} → {CRUPI_REFERENCE_PERIOD[1]}._", ""]
    c = s["crupi"]
    tiers = lambda d: ", ".join(f"{t} {d['by_tier'][t][0]}/{d['by_tier'][t][1]}" for t in "RSP")  # noqa: E731
    unm_cols = ["id", "trigger_time_utc", "detectors", "catalog_name", "S_r1", "CE", "has_data", "focus_r1_max_pm60s",
                "nearest_event_dt_s", "diagnosis"]
    known, unknown = pd.read_csv(v / "matches_crupi_known.csv"), pd.read_csv(v / "matches_crupi_unknown.csv")
    return lines + [
        md_table(acceptance_rows(s)),
        "",
        f"- Known events (Table 11; {c['known']['in_window']} of {c['known']['total']} in the period): found "
        f"**{ratio(c['known']['matched'], c['known']['in_window'])}**; by tier: {tiers(c['known'])}.",
        f"- Unknown events (Table 10; {c['unknown']['in_window']} of {c['unknown']['total']} in the period): found "
        f"**{ratio(c['unknown']['matched'], c['unknown']['in_window'])}**; by tier: {tiers(c['unknown'])}.",
        "",
        "Known events not found:",
        "",
        md_table(known.loc[~known["matched"], unm_cols]),
        "",
        "Unknown events not found:",
        "",
        md_table(unknown.loc[~unknown["matched"], unm_cols]),
        "",
        "Significance, our S against Crupi's (matched events with a numeric reference S):",
        "",
        md_table(pd.read_csv(v / "significance_vs_crupi.csv")),
        "",
    ]


def section_lonely(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 5. Events without counterpart and post-processing flags", ""]
    if not s:
        return lines + [NOT_RUN, ""]
    lonely = pd.read_csv(v / "events_without_counterpart.csv")
    flag_cols = ["saa_edge_short_passage", "saa_region_proximity", "near_zero_prediction"]
    lonely["flags"] = lonely[flag_cols].apply(lambda r: ", ".join(c for c in flag_cols if r[c]) or "none", axis=1)
    by_flag = lonely.groupby("flags").size().rename("events").reset_index().sort_values("events", ascending=False)
    p = f["manifest"].get("parameters", {}).get("flags", {})
    return lines + [
        "Events without counterpart (neither the GBM catalog nor Crupi's tables) are **not discoveries**: they are candidates "
        "to be checked. The flags add columns and never change the event list (definitions in `models/flags.py`): "
        f"`saa_edge_short_passage` (start within {p.get('edge_window_s', 200):.0f} s of an SAA passage whose data gap is not "
        f"masked), `saa_region_proximity` (Fermi within {p.get('region_deg', 3.5)}° of the SAA region), "
        f"`near_zero_prediction` (event ±{p.get('zero_pad_bins', 5)} bins touching a bin with predicted background ≤ 0).",
        "",
        md_table(pd.read_csv(v / "flag_summary.csv")),
        "",
        f"Events without counterpart ({len(lonely)}) by combination of flags:",
        "",
        md_table(by_flag),
        "",
        "Tiers: " + ", ".join(f"{t} {int((lonely['CE'] == t).sum())}" for t in "RSP") + "; distance from the nearest SAA gap: "
        + (f"minimum {lonely['dist_saa_gap_s'].min():.0f} s, median {lonely['dist_saa_gap_s'].median():.0f} s." if len(lonely) else "n/a.")
        + " Full list: `validation/events_without_counterpart.csv`.",
        "",
    ]


def section_classification(f: dict) -> List[str]:
    lines = ["## 6. Classification (Crupi's heuristic baseline)", ""]
    if f["classified"] is None:
        return lines + ["_Step 6 not run: `results/events_classified.csv` missing._", ""]
    pc = f["classified"]["predicted_class"].value_counts()
    lines += [
        "Rules of Crupi's \"manual classification logic\" (upstream `pipeline/script_classification2.py`): thresholds read "
        "from one-vs-rest decision trees and refined by hand. A deliberately simple baseline, to be outperformed by a learned "
        "classifier. The FP rule and the light-curve features `fe_*` (tsfel) are missing. The classifier never reads catalog "
        "columns. It is weak outside GRBs.",
        "",
        "Predicted classes over all events: " + ", ".join(f"{k} {int(n)}" for k, n in pc.items()) + ".",
        "",
    ]
    return lines + classification_vs_crupi_lines(f) + gbm_type_lines(f)


def classification_vs_crupi_lines(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["### 6.1 Predicted class against Crupi's tentative classes", ""]
    table = read_csv(v / "classification_vs_crupi.csv")
    if not s or not s["classification"] or table is None or table.empty:
        return lines + ["_Comparison not available (it needs Crupi's tables and step 6)._", ""]
    c = s["classification"]
    cm = confusion_metrics(table)
    cm["per_class"].to_csv(v / "classification_metrics.csv", index=False)
    rules = read_csv(v / "classification_rules.csv")
    per_class = cm["per_class"].copy()
    for col in ("recall %", "precision %"):
        per_class[col] = per_class[col].map(lambda x: "—" if pd.isna(x) else f"{x:.1f}%")
    return lines + [
        "Crupi's classes are **tentative** (assigned by hand in the paper, sometimes multiple such as `GRB/GF`): they measure "
        "the agreement with his judgement, not the physical nature of the events.",
        "",
        f"Of {c['matched']} events matched to Crupi, predicted class among his tentative ones (multiple included): "
        f"{ratio(c['correct'], c['matched'])}.",
        "",
        f"Confusion matrix on the events with a single Crupi class: **{cm['n']}** events; overall accuracy "
        f"**{cm['correct']}/{cm['n']} ({cm['accuracy']:.1f}%)**. Rows: Crupi's class; columns: predicted class.",
        "",
        "Counts:",
        "",
        md_table(cm["counts"], index=True),
        "",
        "Row percentages (share of each Crupi class in each predicted class; the diagonal is the recall):",
        "",
        md_table(pct_table(cm["row_pct"]), index=True),
        "",
        "Column percentages (composition of each predicted class; the diagonal is the precision):",
        "",
        md_table(pct_table(cm["col_pct"]), index=True),
        "",
        "Per class (support = events with that Crupi class):",
        "",
        md_table(per_class),
        "",
        "Per rule, one-vs-rest (as in Crupi's script):",
        "",
        md_table(rules) if rules is not None else "_(no rows)_",
        "",
    ]


def gbm_type_lines(f: dict) -> List[str]:
    v = f["run"] / "validation"
    lines = ["### 6.2 GBM trigger type against predicted class", ""]
    matches = read_csv(v / "matches_gbm_catalog.csv")
    if matches is None:
        return lines + [NOT_RUN, ""]
    if f["classified"]["trig_ids"].tolist() != f["events"]["trig_ids"].tolist():
        raise JoinError("results/events_classified.csv and results/events_table.csv list different events")
    check_gbm_join(matches, f["events"], MATCH_MARGIN_S, (FOCUS_T_MAX_BINS + 1) * BIN_LENGTH_S)
    counts, row_pct, conc, total = gbm_type_vs_class(matches, f["classified"])
    counts.to_csv(v / "gbm_type_vs_class.csv")
    conc.to_csv(v / "gbm_type_concordance.csv", index=False)
    conc_txt = conc.copy()
    conc_txt["agreement %"] = conc_txt["agreement %"].map(lambda x: f"{x:.1f}%")
    mapping = ", ".join(f"{k}→{c}" for k, c in TYPE_TO_CLASS.items())
    return lines + [
        f"GBM catalog triggers matched to one of our events: {total['n']} (each trigger checked to fall in the window of the "
        f"event it points to, tolerance {MATCH_MARGIN_S:.3f} s). The **GBM type is not the physical nature** of the event: it "
        "is the classification of the flight software and of the duty scientists (UNCERT and LOCLPAR are uncertain by definition).",
        "",
        "Counts (rows: GBM type; columns: predicted class):",
        "",
        md_table(counts, index=True),
        "",
        "Row percentages:",
        "",
        md_table(pct_table(row_pct), index=True),
        "",
        f"Agreement with a **HYPOTHETICAL** mapping ({mapping}): **{total['agree']}/{total['n']} ({total['pct']:.1f}%)**.",
        "",
        md_table(conc_txt),
        "",
    ]


def section_localization(f: dict) -> List[str]:
    lines = ["## 7. Localization", ""]
    if not f["localized"]:
        return lines + ["Not run (`results/events_table_loc.csv` missing).", ""]
    loc = pd.read_csv(f["run"] / "results" / "events_table_loc.csv")
    ok = loc["ra"].notna().sum() if "ra" in loc.columns else 0
    return lines + [
        f"Run: position (PSO on the geometric response of the NaI detectors) for {ok}/{len(loc)} events, in "
        "`results/events_table_loc.csv`. **Not validated** against reference positions: the coordinates are features of the "
        "classifier (distance from Sun and Earth), not a result.",
        "",
    ]


def section_engine(f: dict) -> List[str]:
    man, meta, s = f["manifest"], f["meta"], f["summary"]
    lines = ["## 8. Engine anomalies", ""]
    z = man.get("predicted_zero_cells")
    if z:
        lines.append(f"- Predicted background ≤ 0: {z['cells']} cells out of {z['bins']} bins × {z['channels']} channels "
                     f"({z['bins_any_channel']} bins with at least one channel, {z['bins_all_channels']} with all). "
                     "These bins are excluded from S; neighbouring events carry the flag `near_zero_prediction`"
                     + (f" ({', '.join(str(t) for t in s['flags']['near_zero_events'])})" if s and s["flags"]["near_zero_events"] else "")
                     + ".")
    else:
        lines.append("- Predicted background ≤ 0: count not recorded in the manifest.")
    conv = meta.get("convergence")
    if conv:
        lines.append(f"- Convergence: final val_loss {conv['final_val_loss']:.3f} (best {conv['best_val_loss']:.3f}), "
                     f"ratio to the constant predictor {conv['final_over_constant_median']:.3f} "
                     f"(threshold {conv['max_ratio']}): {OK if conv['ok'] else KO}.")
    elif meta.get("history"):
        val = meta["history"].get("val_loss", [])
        mt = pd.DataFrame(meta.get("metrics", {})).T
        lines.append(f"- Convergence: final val_loss {val[-1]:.3f}, best {min(val):.3f} (epoch {meta.get('best_epoch', '?')}); "
                     f"median test/train MAE over the 36 channels {float((mt['mae_test'] / mt['mae_train']).median()):.3f}. "
                     "Formal convergence check not recorded in the bundle metadata.")
    else:
        lines.append("- Convergence: training history not recorded.")
    if s:
        lines.append(f"- Short SAA passages not masked (data gap ≤ 500 s): {s['flags']['short_unmasked_passages']}; "
                     "the network tends to underestimate the background on the approach (flag `saa_edge_short_passage`).")
    return lines + [""]


def section_lists(f: dict) -> List[str]:
    v = f["run"] / "validation"
    lines = ["## 9. Lists by name", ""]
    matches = read_csv(v / "matches_gbm_catalog.csv")
    if matches is None or f["events"] is None:
        return lines + [NOT_RUN, ""]
    gbm = gbm_named_list(matches, f["events"], f["classified"])
    grb, other = gbm[gbm["type"] == "GRB"], gbm[gbm["type"] != "GRB"]
    grb.to_csv(v / "list_gbm_grb.csv", index=False)
    other.to_csv(v / "list_gbm_other.csv", index=False)
    show = ["trigger_name", "trigger_time", "T90_s", "outcome", "event_trig_ids", "predicted_class"]
    tally = lambda d: ", ".join(f"{k} {int(n)}" for k, n in d["outcome"].value_counts().items())  # noqa: E731
    lines += [
        "Every GBM catalog trigger on the days with data of the period (`validation/list_gbm_grb.csv`, "
        "`validation/list_gbm_other.csv`). Outcome: *detected* (matched to one of our events), *missed* (data present, no "
        "event), *no data* (SAA mask or data gap).",
        "",
        f"### 9.1 GRBs ({len(grb)}: {tally(grb)})",
        "",
        md_table(grb[show], ".1f"),
        "",
        f"### 9.2 Non-GRB triggers ({len(other)}: {tally(other)})",
        "",
        md_table(other[["type"] + show], ".1f"),
        "",
    ]
    known, unknown = read_csv(v / "matches_crupi_known.csv"), read_csv(v / "matches_crupi_unknown.csv")
    if known is None or unknown is None:
        return lines + ["### 9.3 Crupi's events", "", "_Not applicable: Crupi's tables do not cover this period._", ""]
    crupi = crupi_named_list(known, unknown, f["events"], f["classified"])
    crupi.to_csv(v / "list_crupi_events.csv", index=False)
    return lines + [
        f"### 9.3 Crupi's events in the period ({len(crupi)}: {tally(crupi)}; `validation/list_crupi_events.csv`)",
        "",
        md_table(crupi[["set", "id", "catalog_name", "trigger_time_utc", "CE_Crupi", "outcome", "event_trig_ids",
                        "predicted_class", "diagnosis"]]),
        "",
    ]


# ----------------------------------------------------------------------------- RESULTS.md
def results_markdown(run: Path) -> str:
    f = run_facts(run)
    s = f["summary"]
    lines = [
        f"# Results of the run `{f['name']}` ({f['start']} → {f['end']})",
        "",
        "Written by `validation/report.py` (step 9 of `pipeline/pipeline_bkg.py`)"
        + (f"; validation of {s['generated']}, commit `{s['validation_git_commit'][:10]}`" if s else "")
        + ". Every number is read from the files of the run; the full tables are in `validation/` and `results/`.",
        "",
    ]
    for section in (section_run, section_events, section_gbm, section_crupi, section_lonely, section_classification,
                    section_localization, section_engine, section_lists):
        lines += section(f)
    return "\n".join(lines)


def write_results(run: Path) -> Path:
    path = Path(run) / RESULTS_FILE
    path.write_text(results_markdown(run), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="run folder data/runs/<start>_<end>/engine-v<N>[-<label>]")
    args = parser.parse_args()
    setup_logging()
    detail(f"written {rel(write_results(args.run))}")


if __name__ == "__main__":
    main()
