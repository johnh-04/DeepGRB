"""
Tables of the run report (step 9) computed from the files of a run: pure functions, no I/O.

- confusion_metrics: predicted class against Crupi's tentative classes (single-label events):
  counts, row percentages (recall), column percentages (precision), per-class metrics, accuracy.
- check_gbm_join / gbm_type_vs_class: GBM trigger type against the predicted class of the matched
  event, with a HYPOTHETICAL type -> class mapping (the GBM type is not the physical nature).
- gbm_named_list / crupi_named_list: every reference by name with its outcome and predicted class.

The classifier itself never reads catalog columns; these tables only compare its output with them.
"""

from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Hypothesis used only to compare: GBM trigger type -> class of Crupi's rules
TYPE_TO_CLASS = {"GRB": "GRB", "SFLARE": "SF", "TGF": "TGF", "LOCLPAR": "UNC(LP)", "UNCERT": "UNC"}
JOIN_EPS_S = 1e-3


class JoinError(ValueError):
    """The event index of a validation table does not point to the event that contains the trigger."""


def confusion_metrics(table: pd.DataFrame, truth: str = "crupi_class", pred: str = "predicted_class") -> Dict:
    """
    Confusion matrix of the rows with a single reference class ('/' marks multiple tentative classes).
    Returns counts, row_pct (each row sums to 100: recall), col_pct (each column sums to 100: precision),
    per_class (support, recall, precision), accuracy and n.
    """
    single = table[~table[truth].astype(str).str.contains("/")]
    labels = sorted(set(single[truth]) | set(single[pred]))
    counts = pd.crosstab(pd.Categorical(single[truth], categories=labels),
                         pd.Categorical(single[pred], categories=labels), dropna=False)
    counts.index.name, counts.columns.name = "Crupi class", "predicted"
    rows = counts.sum(axis=1)
    cols = counts.sum(axis=0)
    row_pct = counts.div(rows.replace(0, np.nan), axis=0) * 100
    col_pct = counts.div(cols.replace(0, np.nan), axis=1) * 100
    diag = pd.Series(np.diag(counts.to_numpy()), index=labels)
    per_class = pd.DataFrame({
        "class": labels,
        "support (Crupi)": rows.to_numpy(),
        "predicted": cols.to_numpy(),
        "correct": diag.to_numpy(),
        "recall %": (diag / rows.replace(0, np.nan) * 100).to_numpy(),
        "precision %": (diag / cols.replace(0, np.nan) * 100).to_numpy(),
    })
    n = int(counts.to_numpy().sum())
    return {"counts": counts, "row_pct": row_pct, "col_pct": col_pct, "per_class": per_class,
            "accuracy": float(diag.sum() / n * 100) if n else float("nan"), "correct": int(diag.sum()), "n": n}


def check_gbm_join(matches: pd.DataFrame, events: pd.DataFrame, margin_s: float, max_offset_s: float) -> None:
    """
    Every matched trigger must fall in the window of the event its 'event' index points to:
    event start (FOCuS change point) = trig_met - dt_start_s, between start_met - max_offset_s (the
    change point precedes the first triggered bin by at most t_max; the caller adds one bin for the irregular
    MET spacing) and start_met, and
    start - margin <= trig_met <= end_met + margin.
    """
    m = matches[matches["matched"].astype(bool)]
    bad = []
    for _, r in m.iterrows():
        j = int(r["event"])
        if not 0 <= j < len(events):
            bad.append(f"{r.get('name', '?')}: event index {j} outside 0..{len(events) - 1}")
            continue
        t, dt = float(r["trig_met"]), float(r["dt_start_s"])
        t_start = t - dt
        ev = events.iloc[j]
        if dt < -margin_s - JOIN_EPS_S or t > float(ev["end_met"]) + margin_s + JOIN_EPS_S \
                or t_start > float(ev["start_met"]) + JOIN_EPS_S \
                or t_start < float(ev["start_met"]) - max_offset_s - JOIN_EPS_S:
            bad.append(f"{r.get('name', '?')}: trigger {t:.3f} not in event {j} "
                       f"(start {t_start:.3f}, start_met {float(ev['start_met']):.3f}, end_met {float(ev['end_met']):.3f})")
    if bad:
        raise JoinError(f"{len(bad)} matched trigger(s) do not fall in their event: " + "; ".join(bad[:5]))


def _class_of(events_classified: pd.DataFrame, j) -> str:
    j = int(j)
    return str(events_classified.iloc[j]["predicted_class"]) if j >= 0 else ""


def gbm_type_vs_class(matches: pd.DataFrame, classified: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Crosstab GBM trigger type x predicted class for matched triggers (counts and row %), and the
    concordance with TYPE_TO_CLASS per type and in total.
    """
    m = matches[matches["matched"].astype(bool)].copy()
    m["predicted_class"] = [_class_of(classified, j) for j in m["event"]]
    counts = pd.crosstab(m["trigger_type"], m["predicted_class"])
    counts.index.name, counts.columns.name = "GBM type", "predicted"
    row_pct = counts.div(counts.sum(axis=1), axis=0) * 100
    m["expected"] = m["trigger_type"].map(TYPE_TO_CLASS)
    m["agree"] = m["predicted_class"] == m["expected"]
    conc = (m.groupby("trigger_type")
            .agg(matched=("agree", "size"), agreeing=("agree", "sum"))
            .reset_index().rename(columns={"trigger_type": "GBM type"}))
    conc.insert(1, "expected class (hypothesis)", conc["GBM type"].map(TYPE_TO_CLASS).fillna("—"))
    conc["agreement %"] = conc["agreeing"] / conc["matched"] * 100
    total = {"agree": int(m["agree"].sum()), "n": len(m),
             "pct": float(m["agree"].mean() * 100) if len(m) else float("nan")}
    return counts, row_pct, conc, total


def gbm_named_list(matches: pd.DataFrame, events: pd.DataFrame, classified) -> pd.DataFrame:
    """Every GBM trigger of the period (days with data) by name: outcome, event and predicted class."""
    out = pd.DataFrame({
        "trigger_name": matches["trigger_name"], "name": matches["name"], "type": matches["trigger_type"],
        "trigger_time": matches["trigger_time"],
        "T90_s": matches["T90"] if "T90" in matches.columns else np.nan,
        "outcome": np.where(~matches["has_data"].astype(bool), "no data",
                            np.where(matches["matched"].astype(bool), "detected", "missed")),
    })
    ev = matches["event"].astype(int)
    out["event_trig_ids"] = [int(events.iloc[j]["trig_ids"]) if j >= 0 else "" for j in ev]
    out["dt_event_start_s"] = np.where(ev >= 0, matches["dt_start_s"], np.nan)
    out["predicted_class"] = [_class_of(classified, j) if classified is not None else "" for j in ev]
    return out.reset_index(drop=True)


def crupi_named_list(known: pd.DataFrame, unknown: pd.DataFrame, events: pd.DataFrame, classified) -> pd.DataFrame:
    """Crupi's known and unknown events by id: outcome (found / not found + diagnosis) and predicted class."""
    rows = []
    for kind, ref in (("known", known), ("unknown", unknown)):
        for _, r in ref.iterrows():
            j = int(r["event"])
            found = bool(r["matched"])
            rows.append({
                "set": kind, "id": r["id"], "catalog_name": r["catalog_name"], "trigger_time_utc": r["trigger_time_utc"],
                "CE_Crupi": r["CE"], "outcome": "found" if found else "not found",
                "diagnosis": "" if found or pd.isna(r.get("diagnosis")) else r.get("diagnosis"),
                "event_trig_ids": int(events.iloc[j]["trig_ids"]) if found else "",
                "predicted_class": _class_of(classified, j) if found and classified is not None else "",
            })
    return pd.DataFrame(rows)
