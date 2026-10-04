"""
Readable reports of the runs (pipeline step 9), written only from files on disk:

- <run>/RESULTS.md: the scientific report of one run, same sections for every run
  (sections without inputs say so instead of disappearing);
- docs/RUNS.md: one row per run found in data/runs/.

Inputs: <run>/manifest.json, the bundle metadata, <run>/results/*.csv and <run>/validation/
(benchmark/validate.py). No number is written by hand.

Usage (repo root):
    python -m benchmark.report --run data/runs/<start>_<end>/engine-v<N>[-<label>]
    python -m benchmark.report --index          # only docs/RUNS.md
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from connections.utils.config import BASE_DIR, CRUPI_REFERENCE_PERIOD, DOCS_DIR, RUNS_DIR, run_period
from utils.logs import detail, setup_logging
from utils.run_options import bundle_seed, manifest_model, read_manifest

OK, KO = "✔", "✘"
RESULTS_FILE = "RESULTS.md"
RUNS_INDEX = DOCS_DIR / "RUNS.md"


# ----------------------------------------------------------------------------- markdown helpers
def md_table(df: pd.DataFrame, floatfmt: str = ".2f", index: bool = False) -> str:
    """Markdown table without external dependencies (tabulate is not required)."""
    if index:
        df = df.reset_index()
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


def read_csv(path: Path, **kw) -> Optional[pd.DataFrame]:
    return pd.read_csv(path, **kw) if path.exists() else None


def ratio(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else "0/0"


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(BASE_DIR))
    except ValueError:
        return str(path)


# ----------------------------------------------------------------------------- run facts
def run_facts(run: Path) -> dict:
    """Facts shared by RESULTS.md and RUNS.md, from manifest, bundle metadata and outputs."""
    run = Path(run)
    man = read_manifest(run)
    model = manifest_model(man)
    bundle = model.get("bundle")
    bundle_path = BASE_DIR / bundle if bundle else None
    meta_path = bundle_path / "metadata.json" if bundle_path else None
    meta = json.loads(meta_path.read_text()) if meta_path and meta_path.exists() else {}
    seed = model.get("seed", bundle_seed(bundle_path) if bundle_path else None)
    start, end = run_period(run)
    ev = read_csv(run / "results" / "events_table.csv")
    summary_path = run / "validation" / "summary.json"
    return {
        "run": run, "name": run.name, "start": start, "end": end, "manifest": man, "model": model,
        "bundle": bundle, "meta": meta, "seed": seed,
        "events": ev, "summary": json.loads(summary_path.read_text()) if summary_path.exists() else None,
        "flags": read_csv(run / "results" / "events_flags.csv"),
        "classified": read_csv(run / "results" / "events_classified.csv"),
        "localized": (run / "results" / "events_table_loc.csv").exists(),
    }


def seed_text(f: dict) -> str:
    if f["seed"] is not None:
        return str(f["seed"])
    if f["meta"].get("source") == "legacy_h5":
        return "non registrato (modello legacy)"
    return "non registrato"


# ----------------------------------------------------------------------------- RESULTS.md
def section_run(f: dict) -> List[str]:
    man, model, meta = f["manifest"], f["model"], f["meta"]
    p = man.get("parameters", {})
    history = man.get("runs", [])
    reused = man.get("reused_from")
    lines = [
        "## 1. Run, rete e parametri",
        "",
        f"- Periodo: **{f['start']} → {f['end']}** (giorni UTC inclusi); run `{rel(f['run'])}`.",
        f"- Motore: engine v{p.get('engine_version', '?')}; eseguito dai commit "
        + ", ".join(f"`{h.get('git_commit', '?')[:10]}`" + (" (codice modificato)" if h.get("code_dirty") else "") for h in history)
        + ".",
        f"- Rete: bundle `{f['bundle'] or '?'}`; seed di training {seed_text(f)}; "
        f"checksum sha256 del bundle `{model.get('checksum', 'non registrato')}`.",
    ]
    if reused:
        lines.append(f"- Predizioni (step 3) e trigger (step 4) riusati da `{reused['run']}` "
                     f"(engine v{reused['engine_version']}, {reused['how']}).")
    if meta.get("source") == "trained":
        h = meta.get("hyperparameters", {})
        lines.append(f"- Addestramento: {meta.get('epochs_run', '?')} epoche (migliore {meta.get('best_epoch', '?')}), "
                     f"{h.get('units', '?')} unità, lr {h.get('lr', '?')}, batch {h.get('batch_size', '?')}, "
                     f"{meta.get('training_seconds', '?')} s su {', '.join(meta.get('devices', [])) or '?'}.")
    elif meta.get("source") == "legacy_h5":
        lines.append(f"- Addestramento: {meta.get('note', 'modello legacy')}.")
    focus, trig = p.get("focus", {}), p.get("trigger", {})
    lines += [
        f"- Parametri: bin {p.get('bin_length_s')} s; FOCuS mu_min {focus.get('mu_min')}, t_max {focus.get('t_max_bins')} bin "
        f"(ingresso: {focus.get('input')}); soglia {trig.get('threshold_sigma')} σ in {trig.get('range')} su ≥ "
        f"{trig.get('min_detectors')} rivelatori; merge {p.get('merge_s')} s; maschera SAA ±{p.get('saa_exclusion_bins_each_side')} "
        f"bin attorno ai buchi > {p.get('saa_gap_s')} s.",
        "",
    ]
    return lines


def section_events(f: dict) -> List[str]:
    ev, s = f["events"], f["summary"]
    lines = ["## 2. Eventi", ""]
    if ev is None:
        return lines + ["_Step 5 non eseguito: `results/events_table.csv` assente._", ""]
    ce = {c: int((ev["CE"] == c).sum()) for c in "RSP"}
    lines.append(f"- Totale: **{len(ev)}**; tier CE: R {ce['R']}, S {ce['S']}, P {ce['P']} "
                 "(R: più rivelatori e più bande; S: più rivelatori, una banda; P: gli altri).")
    if s:
        e = s["events"]
        lines.append(f"- Abbinati al catalogo trigger GBM: {e['match_gbm']}"
                     + (f"; a Crupi noti: {e['match_crupi_known']}; a Crupi inediti: {e['match_crupi_unknown']}" if s["crupi"] else "")
                     + f". Senza controparte: **{e['without_counterpart']}** "
                     f"({e['without_counterpart'] / max(s['data_days'], 1):.2f} al giorno su {s['data_days']} giorni con dati).")
    return lines + [""]


def section_gbm(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 3. Catalogo ufficiale Fermi-GBM", ""]
    if not s:
        return lines + ["_Validazione (step 8) non eseguita._", ""]
    g = s["gbm"]
    lines += [
        f"Regola primaria: abbinamento uno-a-uno, istante del trigger entro [inizio evento − {s['match_margin_s']:.3f} s, "
        f"fine evento + {s['match_margin_s']:.3f} s].",
        "",
        f"- Trigger nel periodo, nei giorni con dati: {g['catalog_triggers']}; senza dati validi all'istante (maschera SAA/buchi): "
        f"{g['missing_no_data']}; disponibili: {g['available']}; rivelati: **{g['detected']}**.",
        f"- Entro ±150 s da un buco > 500 s: {g['near_saa_150s']} trigger.",
        "",
        md_table(pd.read_csv(v / "gbm_by_type.csv")),
        "",
        "GRB del Burst Catalog (T90):",
        "",
    ]
    rows = [{"": "GRB nel periodo", "questa run": g["grb_total"]},
            {"": "senza dati (SAA)", "questa run": g["grb_missing"]},
            {"": "rivelati / disponibili", "questa run": ratio(g["grb_detected"], g["grb_available"])},
            {"": "T90 > 4.096 s", "questa run": ratio(g["long_detected"], g["long_available"])},
            {"": "T90 ≤ 4.096 s", "questa run": ratio(g["short_detected"], g["short_available"])}]
    table = pd.DataFrame(rows)
    if s["crupi"]:
        P = s["crupi"]["paper"]
        table["paper (fino al 9/07/2019)"] = [P["grb_burst_catalog"], P["grb_missing"], f"{P['grb_detected']}/{P['grb_available']}",
                                             f"{P['long_detected']}/{P['long_available']} (88%)",
                                             f"{P['short_detected']}/{P['short_available']} (34%)"]
    lines += [md_table(table), "", "Sensibilità alla regola di abbinamento:", "", md_table(pd.read_csv(v / "sensitivity.csv")), ""]
    return lines


def acceptance_rows(s: dict) -> pd.DataFrame:
    c, g = s["crupi"], s["gbm"]
    kn, un = c["known"], c["unknown"]
    rs_k, rs_u = c["known_RS"], c["unknown_RS"]
    rows = [
        ("Noti di Crupi ritrovati ≥ 90%", ratio(kn["matched"], kn["in_window"]), kn["in_window"] and kn["matched"] / kn["in_window"] >= 0.9),
        ("Tutti gli R e S noti ritrovati", ratio(*rs_k), rs_k[0] == rs_k[1]),
        ("Inediti R+S ritrovati ≥ 90%", ratio(*rs_u), bool(rs_u[1]) and rs_u[0] / rs_u[1] >= 0.9),
        ("Inediti complessivi ≥ 70%", ratio(un["matched"], un["in_window"]), un["in_window"] and un["matched"] / un["in_window"] >= 0.7),
    ]
    out = [{"criterio (docs/WORKING_RULES.md §6)": a, "misurato": b, "esito": OK if ok else KO} for a, b, ok in rows]
    out += [
        {"criterio (docs/WORKING_RULES.md §6)": "Recall GRB T90 > 4.096 s ~ 88% (paper)", "misurato": ratio(g["long_detected"], g["long_available"]),
         "esito": "ordine di grandezza"},
        {"criterio (docs/WORKING_RULES.md §6)": "Recall GRB T90 ≤ 4.096 s ~ 34% (paper)", "misurato": ratio(g["short_detected"], g["short_available"]),
         "esito": "ordine di grandezza"},
        {"criterio (docs/WORKING_RULES.md §6)": "Numero eventi ~ 100 (paper, fino al 9 luglio)", "misurato": str(s["events"]["total"]),
         "esito": "informativo: dipende dalla rete"},
    ]
    return pd.DataFrame(out)


def section_crupi(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 4. Confronto con Crupi et al. (2023)", ""]
    if not s:
        return lines + ["_Validazione (step 8) non eseguita._", ""]
    if not s["crupi"]:
        return lines + [f"_Non applicabile: le tabelle di Crupi coprono solo {CRUPI_REFERENCE_PERIOD[0]} → {CRUPI_REFERENCE_PERIOD[1]}._", ""]
    c = s["crupi"]
    tiers = lambda d: ", ".join(f"{t} {d['by_tier'][t][0]}/{d['by_tier'][t][1]}" for t in "RSP")  # noqa: E731
    unm_cols = ["id", "trigger_time_utc", "detectors", "catalog_name", "S_r1", "CE", "has_data", "focus_r1_max_pm60s",
                "nearest_event_dt_s", "diagnosis"]
    known, unknown = pd.read_csv(v / "matches_crupi_known.csv"), pd.read_csv(v / "matches_crupi_unknown.csv")
    lines += [
        md_table(acceptance_rows(s)),
        "",
        f"- Noti (Tabella 11; in finestra {c['known']['in_window']} di {c['known']['total']}): ritrovati "
        f"**{ratio(c['known']['matched'], c['known']['in_window'])}**; per tier: {tiers(c['known'])}.",
        f"- Inediti (Tabella 10; in finestra {c['unknown']['in_window']} di {c['unknown']['total']}): ritrovati "
        f"**{ratio(c['unknown']['matched'], c['unknown']['in_window'])}**; per tier: {tiers(c['unknown'])}.",
        "",
        "Noti non ritrovati:",
        "",
        md_table(known.loc[~known["matched"], unm_cols]),
        "",
        "Inediti non ritrovati:",
        "",
        md_table(unknown.loc[~unknown["matched"], unm_cols]),
        "",
        "Significatività, nostro S rispetto a quello di Crupi (eventi abbinati con S di riferimento numerico):",
        "",
        md_table(pd.read_csv(v / "significance_vs_crupi.csv")),
        "",
    ]
    sec1 = read_csv(v / "section1_cases.csv")
    if sec1 is not None and not sec1.empty:
        lines += ["Casi del §1 di docs/WORKING_RULES.md (i due \"sub-threshold GRB\" del vecchio log):", "", md_table(sec1), ""]
    return lines


def section_lonely(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 5. Eventi senza controparte e flag di post-processing", ""]
    if not s:
        return lines + ["_Validazione (step 8) non eseguita._", ""]
    lonely = pd.read_csv(v / "events_without_counterpart.csv")
    flag_cols = ["saa_edge_short_passage", "saa_region_proximity", "near_zero_prediction"]
    lonely["flag"] = lonely[flag_cols].apply(lambda r: ", ".join(c for c in flag_cols if r[c]) or "nessuno", axis=1)
    by_flag = lonely.groupby("flag").size().rename("eventi").reset_index().sort_values("eventi", ascending=False)
    p = f["manifest"].get("parameters", {}).get("flags", {})
    lines += [
        "Gli eventi senza controparte (né catalogo GBM né tabelle di Crupi) **non sono scoperte**: sono candidati da verificare. "
        "I flag aggiungono colonne e non cambiano l'elenco degli eventi (definizioni in `models/flags.py` e `docs/ORBIT_ANALYSIS.md`): "
        f"`saa_edge_short_passage` (inizio entro {p.get('edge_window_s', 200):.0f} s da un passaggio SAA il cui buco non è mascherato), "
        f"`saa_region_proximity` (Fermi entro {p.get('region_deg', 3.5)}° dalla regione SAA), "
        f"`near_zero_prediction` (evento ±{p.get('zero_pad_bins', 5)} bin che tocca un bin con fondo previsto ≤ 0).",
        "",
        md_table(pd.read_csv(v / "flag_summary.csv")),
        "",
        f"Eventi senza controparte ({len(lonely)}) per combinazione di flag:",
        "",
        md_table(by_flag),
        "",
        "Tier: " + ", ".join(f"{t} {int((lonely['CE'] == t).sum())}" for t in "RSP") + "; distanza dal buco SAA più vicino: "
        + (f"minima {lonely['dist_saa_gap_s'].min():.0f} s, mediana {lonely['dist_saa_gap_s'].median():.0f} s." if len(lonely) else "n/a.")
        + " Elenco completo: `validation/events_without_counterpart.csv`.",
        "",
    ]
    return lines


def section_classification(f: dict) -> List[str]:
    s, v = f["summary"], f["run"] / "validation"
    lines = ["## 6. Classificazione (baseline euristica di Crupi)", ""]
    if f["classified"] is None:
        return lines + ["_Step 6 non eseguito: `results/events_classified.csv` assente._", ""]
    pc = f["classified"]["predicted_class"].value_counts()
    lines += [
        "Regole della \"manual classification logic\" di Crupi (`pipeline/script_classification2.py` upstream): soglie lette da "
        "decision tree uno-contro-resto e rifinite a mano. Baseline volutamente semplice, da superare con XGBoost (fase 6). "
        "Mancano la regola FP e le feature `fe_*` (tsfel). Il classificatore non legge le colonne del catalogo "
        "(`tests/test_classifier.py`). Fuori dai GRB è debole.",
        "",
        "Classi predette su tutti gli eventi: " + ", ".join(f"{k} {int(n)}" for k, n in pc.items()) + ".",
        "",
    ]
    if not s or not s["classification"]:
        return lines + ["_Confronto con un riferimento non disponibile (servono le tabelle di Crupi)._", ""]
    c = s["classification"]
    rules = read_csv(v / "classification_rules.csv")
    cm = read_csv(v / "classification_confusion.csv", index_col=0)
    lines += [
        f"Su {c['matched']} eventi abbinati a Crupi, classe predetta tra quelle tentative di Crupi: {ratio(c['correct'], c['matched'])}.",
        "",
        "Per regola, uno-contro-resto:",
        "",
        md_table(rules) if rules is not None else "_(nessuna riga)_",
        "",
        f"Matrice di confusione sugli eventi con classe Crupi univoca ({c['single_label']}; righe Crupi, colonne predetta):",
        "",
        "```",
        cm.to_string() if cm is not None else "",
        "```",
        "",
    ]
    return lines


def section_localization(f: dict) -> List[str]:
    lines = ["## 7. Localizzazione", ""]
    if not f["localized"]:
        return lines + ["Non eseguita (`results/events_table_loc.csv` assente).", ""]
    loc = pd.read_csv(f["run"] / "results" / "events_table_loc.csv")
    ok = loc["ra"].notna().sum() if "ra" in loc.columns else 0
    return lines + [
        f"Eseguita: posizione (PSO sulla risposta geometrica dei NaI) per {ok}/{len(loc)} eventi, in `results/events_table_loc.csv`. "
        "**Non validata** rispetto a posizioni di riferimento: le coordinate servono come feature del classificatore "
        "(distanza da Sole e Terra), non come risultato.",
        "",
    ]


def section_engine(f: dict) -> List[str]:
    man, meta, s = f["manifest"], f["meta"], f["summary"]
    lines = ["## 8. Anomalie del motore", ""]
    z = man.get("predicted_zero_cells")
    if z:
        lines.append(f"- Fondo previsto ≤ 0: {z['cells']} celle su {z['bins']} bin × {z['channels']} canali "
                     f"({z['bins_any_channel']} bin con almeno un canale, {z['bins_all_channels']} con tutti). "
                     "Da engine v3 quei bin sono esclusi dal calcolo di S; gli eventi vicini hanno il flag `near_zero_prediction`"
                     + (f" ({', '.join(str(t) for t in s['flags']['near_zero_events'])})" if s and s["flags"]["near_zero_events"] else "")
                     + ".")
    else:
        lines.append("- Fondo previsto ≤ 0: conteggio non registrato nel manifest.")
    conv = meta.get("convergence")
    if conv:
        lines.append(f"- Convergenza: val_loss finale {conv['final_val_loss']:.3f} (migliore {conv['best_val_loss']:.3f}), "
                     f"rapporto con il predittore costante {conv['final_over_constant_median']:.3f} "
                     f"(soglia {conv['max_ratio']}): {OK if conv['ok'] else KO}.")
    elif meta.get("history"):
        val = meta["history"].get("val_loss", [])
        mt = pd.DataFrame(meta.get("metrics", {})).T
        lines.append(f"- Convergenza: val_loss finale {val[-1]:.3f}, migliore {min(val):.3f} (epoca {meta.get('best_epoch', '?')}); "
                     f"MAE test/train mediano sui 36 canali {float((mt['mae_test'] / mt['mae_train']).median()):.3f}. "
                     "Controllo formale non registrato (bundle precedente all'introduzione del controllo).")
    else:
        lines.append("- Convergenza: storia dell'addestramento non registrata (modello legacy).")
    if s:
        lines.append(f"- Passaggi SAA brevi non mascherati (buco ≤ 500 s): {s['flags']['short_unmasked_passages']}; "
                     "la rete tende a sottostimare il fondo nell'avvicinamento (flag `saa_edge_short_passage`).")
        if s["stability"]:
            lines.append("- Stabilità rispetto alla rete (stesso periodo): " + "; ".join(
                f"con `{x['bundle']}` (run `{x['run']}`, {x['events']} eventi): {x['pairs']} coppie, {x['only_here']} solo qui, "
                f"{x['only_there']} solo là" for x in s["stability"]) + ".")
    return lines + [""]


def results_markdown(run: Path) -> str:
    f = run_facts(run)
    s = f["summary"]
    lines = [
        f"# Resoconto della run `{f['name']}` ({f['start']} → {f['end']})",
        "",
        "Generato da `benchmark/report.py` (step 9 di `pipeline/pipeline_bkg.py`)"
        + (f"; validazione del {s['generated']}, commit `{s['validation_git_commit'][:10]}`" if s else "")
        + ". Tutti i numeri sono letti da file della run; le tabelle complete sono in `validation/` e `results/`.",
        "",
    ]
    for section in (section_run, section_events, section_gbm, section_crupi, section_lonely, section_classification,
                    section_localization, section_engine):
        lines += section(f)
    return "\n".join(lines)


def write_results(run: Path) -> Path:
    path = Path(run) / RESULTS_FILE
    path.write_text(results_markdown(run), encoding="utf-8")
    return path


# ----------------------------------------------------------------------------- RUNS.md
def all_runs() -> List[Path]:
    return sorted(p for p in RUNS_DIR.glob("*/engine-v*") if p.is_dir() and (p / "manifest.json").exists())


def runs_index_row(run: Path) -> dict:
    f = run_facts(run)
    ev, s = f["events"], f["summary"]
    row = {
        "periodo": f"{f['start']} → {f['end']}", "run": f"`{f['name']}`",
        "rete": f"`{Path(f['bundle']).name if f['bundle'] else '?'}` (seed {seed_text(f)})",
        "eventi R/S/P": f"{len(ev)} ({'/'.join(str(int((ev['CE'] == c).sum())) for c in 'RSP')})" if ev is not None else "—",
        "GBM rivelati": f"{s['gbm']['detected']}/{s['gbm']['available']}" if s else "—",
        "GRB": f"{s['gbm']['grb_detected']}/{s['gbm']['grb_available']}" if s else "—",
        "Crupi noti": "—", "Crupi inediti": "—",
        "senza controparte": str(s["events"]["without_counterpart"]) if s else "—",
        "loc/class": ("✔" if f["localized"] else "—") + "/" + ("✔" if f["classified"] is not None else "—"),
        "resoconto": f"[RESULTS.md](../{rel(run / RESULTS_FILE)})" if (run / RESULTS_FILE).exists() else "—",
    }
    if s and s["crupi"]:
        c = s["crupi"]
        row["Crupi noti"] = f"{c['known']['matched']}/{c['known']['in_window']}"
        row["Crupi inediti"] = f"{c['unknown']['matched']}/{c['unknown']['in_window']}"
    return row


def write_runs_index() -> Path:
    rows = [runs_index_row(r) for r in all_runs()]
    lines = [
        "# Run del motore",
        "",
        "Generato da `python -m benchmark.report --index` (anche allo step 9 della pipeline): una riga per ogni run in `data/runs/` "
        "con un `manifest.json`. Valori letti dai file della run; \"—\" = step non eseguito o non applicabile.",
        "",
        md_table(pd.DataFrame(rows)),
        "",
    ]
    RUNS_INDEX.write_text("\n".join(lines), encoding="utf-8")
    return RUNS_INDEX


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, help="run folder data/runs/<start>_<end>/engine-v<N>[-<label>]")
    parser.add_argument("--index", action="store_true", help="only rewrite docs/RUNS.md")
    args = parser.parse_args()
    setup_logging()
    if args.run is None and not args.index:
        parser.error("give --run or --index")
    if args.run is not None:
        detail(f"written {rel(write_results(args.run))}")
    detail(f"written {rel(write_runs_index())}")


if __name__ == "__main__":
    main()
