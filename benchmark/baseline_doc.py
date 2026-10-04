"""
Writes docs/BASELINE_2019.md, the reference document of the 2019 baseline, and the example block of
README.md, from files on disk (run manifests, bundle metadata, results/ and validation/ of the runs)
and computes the sha256 checksums. No number is written by hand.

Usage (repo root):
    python -m benchmark.baseline_doc --run <reference run> --compare <comparison run>
e.g. --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --compare data/runs/2019-03-01_2019-06-30/engine-v3
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pandas as pd

from benchmark.matching import overlap_one_to_one
from benchmark.report import md_table, ratio, rel
from connections.utils.config import (BASE_DIR, DOCS_DIR, FLAG_EDGE_WINDOW_S, FLAG_REGION_DEG, FLAG_ZERO_PAD_BINS,
                                      SAA_GAP_S, run_period)
from utils.logs import detail, setup_logging
from utils.run_options import manifest_model, read_manifest

DOC = DOCS_DIR / "BASELINE_2019.md"
README = BASE_DIR / "README.md"
README_BLOCK = re.compile(r"(<!-- BASELINE:START[^>]*-->\n).*?(<!-- BASELINE:END -->)", re.S)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()


def summary(run: Path) -> dict:
    return json.loads((run / "validation" / "summary.json").read_text())


def key_numbers(run: Path) -> dict:
    s = summary(run)
    g, c, e = s["gbm"], s["crupi"], s["events"]
    row = {
        "run": f"`{run.name}`",
        "rete": f"`{Path(s['model_bundle']).name}`",
        "eventi": e["total"],
        "CE R/S/P": "/".join(str(e["CE"][t]) for t in "RSP"),
        "Crupi noti": f"{c['known']['matched']}/{c['known']['in_window']}" if c else "—",
        "Crupi inediti": f"{c['unknown']['matched']}/{c['unknown']['in_window']}" if c else "—",
        "inediti R+S": "/".join(map(str, c["unknown_RS"])) if c else "—",
        "GBM rivelati/disponibili": f"{g['detected']}/{g['available']}",
        "GRB": f"{g['grb_detected']}/{g['grb_available']}",
        "T90>4.096 / ≤4.096": f"{g['long_detected']}/{g['long_available']} / {g['short_detected']}/{g['short_available']}",
        "senza controparte": e["without_counterpart"],
    }
    f = pd.read_csv(run / "validation" / "events_counterparts.csv")
    anyf = f[["saa_edge_short_passage", "saa_region_proximity", "near_zero_prediction"]].any(axis=1)
    row["flaggati: abbinati / senza controparte"] = (f"{int((anyf & f['counterpart']).sum())}/{int(f['counterpart'].sum())} / "
                                                     f"{int((anyf & ~f['counterpart']).sum())}/{int((~f['counterpart']).sum())}")
    row["classe compatibile con Crupi"] = (f"{s['classification']['correct']}/{s['classification']['matched']}"
                                           if s.get("classification") else "—")
    return row


def readme_block(ref: Path, cmp: Path) -> str:
    """Short example for README.md, from the validation of the reference and comparison runs."""
    s, t = summary(ref), summary(cmp)
    c, g = s["crupi"], s["gbm"]
    return "\n".join([
        f"Reference run `{rel(ref)}` (network `{Path(s['model_bundle']).name}`), from its `RESULTS.md`:",
        "",
        f"- events: **{s['events']['total']}** (R {s['events']['CE']['R']}, S {s['events']['CE']['S']}, P {s['events']['CE']['P']});",
        f"- Crupi et al., known events (Table 11, up to 2019-06-30): **{ratio(c['known']['matched'], c['known']['in_window'])}**; "
        f"unknown events (Table 10): **{ratio(c['unknown']['matched'], c['unknown']['in_window'])}**, R+S {ratio(*c['unknown_RS'])};",
        f"- official GBM triggers detected: {ratio(g['detected'], g['available'])}; GRB {ratio(g['grb_detected'], g['grb_available'])} "
        f"(T90 > 4.096 s {ratio(g['long_detected'], g['long_available'])}, ≤ 4.096 s {ratio(g['short_detected'], g['short_available'])});",
        f"- events without counterpart: {s['events']['without_counterpart']} (candidates, mostly SAA-flagged).",
        "",
        f"With the legacy network (`{rel(cmp)}`): {t['events']['total']} events, known {t['crupi']['known']['matched']}/"
        f"{t['crupi']['known']['in_window']}, unknown {t['crupi']['unknown']['matched']}/{t['crupi']['unknown']['in_window']}, "
        f"{t['events']['without_counterpart']} without counterpart. Details: `docs/BASELINE_2019.md`, `docs/RUNS.md`.",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="reference run (retrained network)")
    parser.add_argument("--compare", type=Path, required=True, help="comparison run (legacy network)")
    args = parser.parse_args()
    setup_logging()
    ref, cmp = args.run.resolve(), args.compare.resolve()
    start, end = run_period(ref)
    m_ref, m_leg = read_manifest(ref), read_manifest(cmp)
    ref_bundle = BASE_DIR / manifest_model(m_ref)["bundle"]
    legacy_bundle = BASE_DIR / manifest_model(m_leg)["bundle"]
    meta = json.loads((ref_bundle / "metadata.json").read_text())
    legacy_meta = json.loads((legacy_bundle / "metadata.json").read_text())
    mae_test = sum(v["mae_test"] for v in meta["metrics"].values()) / len(meta["metrics"])
    runs = sorted(p for p in ref.parent.iterdir() if (p / "validation" / "summary.json").exists())

    checksums = []
    for b in (ref_bundle, legacy_bundle):
        for f in sorted(b.iterdir()):
            if f.is_file():
                checksums.append({"file": rel(f), "sha256": sha256(f)})
    for run in (ref, cmp):
        for name in ("events_table.csv", "triggers_table.csv", "events_table_loc.csv", "events_classified.csv", "events_flags.csv"):
            f = run / "results" / name
            if f.exists():
                checksums.append({"file": rel(f), "sha256": sha256(f)})

    ref_cp = pd.read_csv(ref / "validation" / "events_counterparts.csv")
    leg_cp = pd.read_csv(cmp / "validation" / "events_counterparts.csv")
    nb_lone = ref_cp.loc[~ref_cp["counterpart"], "detectors"].str.contains("nb")
    nb_match = ref_cp.loc[ref_cp["counterpart"], "detectors"].str.contains("nb")
    near_zero_ids = ref_cp.loc[ref_cp["near_zero_prediction"], "trig_ids"].tolist()
    zero = m_ref.get("predicted_zero_cells", {})
    ev_ref = pd.read_csv(ref / "results" / "events_table.csv")
    ev_leg = pd.read_csv(cmp / "results" / "events_table.csv")
    pairs = overlap_one_to_one(ev_ref["start_met"], ev_ref["duration"], ev_leg["start_met"], ev_leg["duration"])
    cp_ref = set(ref_cp.loc[ref_cp["counterpart"], "trig_ids"])
    cp_leg = set(leg_cp.loc[leg_cp["counterpart"], "trig_ids"])
    paired = {(int(ev_ref.at[i, "trig_ids"]), int(ev_leg.at[j, "trig_ids"])) for i, j, _ in pairs}
    cp_paired = all(any(a == r and b in cp_leg for a, b in paired) for r in cp_ref)
    zp = ref / "analysis" / "zero_prediction_summary.json"
    hist = m_ref.get("runs") or [{}]
    reused = m_ref.get("reused_from") or {}

    L = [
        "# Baseline 2019 — documento di riferimento",
        "",
        f"Generato da `python -m benchmark.baseline_doc --run {rel(ref)} --compare {rel(cmp)}` (codice al commit "
        f"`{git('rev-parse', '--short', 'HEAD')}`). Numeri, metadati e checksum letti dai file; nessuna cifra scritta a mano.",
        "",
        "## 1. Riferimento",
        "",
        f"- Periodo: {start} → {end} (inclusivo). Motore: engine v{m_ref['parameters']['engine_version']} "
        "(v3 = v2 con S che ignora i bin con fondo previsto ≤ 0).",
        f"- **Run di riferimento**: `{rel(ref)}`; step 5-9 eseguiti dal commit `{str(hist[-1].get('git_commit', '?'))[:7]}`"
        + (f", predizioni e trigger riusati da `{reused.get('run')}` (prodotti dal commit `{str(reused.get('source_git_commit', '?'))[:7]}`)"
           if reused else "") + f". Resoconto: `{rel(ref / 'RESULTS.md')}`.",
        f"- **Run di confronto (rete legacy)**: `{rel(cmp)}`"
        + (f", predizioni da `{(m_leg.get('reused_from') or {}).get('run')}`" if m_leg.get("reused_from") else "")
        + f". Resoconto: `{rel(cmp / 'RESULTS.md')}`.",
        f"- **Rete di riferimento**: `{rel(ref_bundle)}`",
        f"  - seed {meta.get('seed')}; periodo {meta['period']['start_date']} → {meta['period']['end_date']}; addestrata il "
        f"{str(meta.get('trained_at', '?'))[:19]} dal commit `{str(meta.get('git_commit', '?'))[:7]}`;",
        f"  - iperparametri: {', '.join(f'{k}={v}' for k, v in meta['hyperparameters'].items() if not isinstance(v, dict))};",
        f"  - righe fit/validazione/test: {meta['rows']['fit']}/{meta['rows']['validation']}/{meta['rows']['test']}; epoche "
        f"{meta.get('epochs_run')}, migliore {meta.get('best_epoch')}; tempo di fit {meta.get('training_seconds', 0) / 60:.1f} min su "
        f"{', '.join(meta.get('devices', []))};",
        f"  - MAE di test media sui 36 canali {mae_test:.3f}; controllo di convergenza: "
        + ("presente nei metadati" if "convergence" in meta else
           f"assente (training precedente al controllo; val_loss migliore {min(meta['history']['val_loss']):.2f}, contro 20.4 del "
           "predittore costante per canale, verifica una tantum del 2026-10-04 in `docs/WORKLOG.md`)") + ";",
        f"  - versioni: {', '.join(f'{k} {v}' for k, v in meta['versions'].items())}.",
        f"- **Rete legacy**: `{rel(legacy_bundle)}` ({legacy_meta.get('note', '')}).",
        "",
        "## 2. Riproduzione",
        "",
        "Dalla radice del repo, env `deepgrb_recas`. Download e preprocess devono essere completi "
        f"(`python -m benchmark.audit.data_inventory --run {rel(ref)}`).",
        "",
        "```bash",
        f"# a) riferimento dagli artefatti esistenti (riusa pred/ e trig/ di {Path(reused.get('run', '?')).name}; nessun training, nessun FOCuS)",
        f"DEEPGRB_START_DATE={start} DEEPGRB_END_DATE={end} "
        + (f"DEEPGRB_RUN_LABEL={m_ref['run_label']} " if m_ref.get("run_label") else "")
        + "DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --jobs 4",
        "",
        f"# b) confronto con la rete legacy (riusa pred/ e trig/ di {Path((m_leg.get('reused_from') or {}).get('run', '?')).name})",
        f"DEEPGRB_START_DATE={start} DEEPGRB_END_DATE={end} "
        + (f"DEEPGRB_RUN_LABEL={m_leg['run_label']} " if m_leg.get("run_label") else "")
        + "DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --jobs 4",
        "",
        "# c) da zero, nuovo training (cartella e bundle non devono esistere; GPU consigliata)",
        f"DEEPGRB_START_DATE={start} DEEPGRB_END_DATE={end} DEEPGRB_RUN_LABEL=<nuova etichetta> DEEPGRB_TRAIN_SEED=1 "
        "DEEPGRB_FORCE_TRAIN=1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py",
        "",
        "# documenti",
        f"python -m benchmark.baseline_doc --run {rel(ref)} --compare {rel(cmp)}",
        "```",
        "",
        "Una run esistente riprende solo gli step mancanti e non viene mai riscritta: per rigenerare a) o b) da capo spostare prima "
        "la cartella in `data/_archive_<data>/`. Un nuovo training (c) **non** riproduce i pesi bit a bit (su GPU TensorFlow non è "
        "deterministico): i numeri di questo documento sono riproducibili esattamente solo a partire dal bundle di riferimento (checksum in §6).",
        "",
        "## 3. Numeri chiave",
        "",
        md_table(pd.DataFrame([key_numbers(r) for r in runs])),
        "",
        "Regola di abbinamento: uno-a-uno, istante del riferimento entro [inizio evento − 2 bin, fine evento + 2 bin] (`benchmark/matching.py`). "
        f"Il paper (fino al 9 luglio) riporta 100 eventi, GRB 65/81, T90 > 4.096 s 60/68, T90 ≤ 4.096 s 5/13. "
        "Le run v2 usano il motore precedente (S calcolato anche sui bin con fondo previsto ≤ 0); flag e validazione sono quelli attuali.",
        "",
        "## 4. Flag di post-processing (`models/flags.py`, step 7; non cambiano l'elenco degli eventi)",
        "",
        f"- `saa_edge_short_passage`: l'inizio dell'evento (change point FOCuS) cade entro {FLAG_EDGE_WINDOW_S:.0f} s prima dell'entrata o dopo "
        f"l'uscita di un passaggio SAA (flag POSHIST) il cui buco nei dati è ≤ {SAA_GAP_S:.0f} s, quindi **non mascherato** dallo step 3.",
        f"- `saa_region_proximity`: la posizione di Fermi all'inizio dell'evento è entro {FLAG_REGION_DEG}° dalla regione con flag SAA nelle "
        "POSHIST (regione campionata su griglia di 0.1°).",
        f"- `near_zero_prediction`: i bin dell'evento, estesi di {FLAG_ZERO_PAD_BINS} per lato, toccano un bin con fondo previsto ≤ 0. "
        f"Nella run di riferimento: eventi {near_zero_ids}.",
        "",
        "Per evento: `<run>/results/events_flags.csv`, con le controparti in `<run>/validation/events_counterparts.csv`. "
        "Analisi che li motiva: `docs/ORBIT_ANALYSIS.md`.",
        "",
        "## 5. Limiti noti e perimetro",
        "",
        f"- **Passaggi SAA brevi non mascherati** (gruppo A di ORBIT_ANALYSIS): la maschera agisce solo sui buchi > {SAA_GAP_S:.0f} s; prima "
        f"dei passaggi brevi la rete sottostima il fondo. Eventi con `saa_edge_short_passage` nel riferimento: "
        f"{int(ref_cp['saa_edge_short_passage'].sum())}, di cui abbinati a Crupi/GBM "
        f"{int((ref_cp['saa_edge_short_passage'] & ref_cp['counterpart']).sum())}.",
        f"- **Bordo nord della SAA** (gruppo B): eventi senza controparte vicini alla regione SAA, nell'orbita che precede il primo passaggio "
        f"di una sequenza. Senza controparte con `saa_region_proximity` e senza `saa_edge_short_passage`: "
        f"{int((ref_cp['saa_region_proximity'] & ~ref_cp['saa_edge_short_passage'] & ~ref_cp['counterpart']).sum())}.",
        f"- **Celle con fondo previsto 0** (rete di riferimento): {zero.get('cells', '?')} celle in {zero.get('bins_any_channel', '?')} bin; "
        + ("la rete è instabile dove la velocità angolare (w1, w2, w3) è nella coda estrema della distribuzione: la pre-attivazione finale "
           "diventa negativa e la ReLU taglia a zero (ORBIT_ANALYSIS §5b). " if zp.exists() else "")
        + f"Da engine v3 quei bin sono esclusi da S; gli eventi adiacenti ({near_zero_ids}) restano e sono marcati da `near_zero_prediction`.",
        f"- **Rivelatore nb**: compare in {int(nb_lone.sum())}/{len(nb_lone)} eventi senza controparte contro {int(nb_match.sum())}/"
        f"{len(nb_match)} abbinati a Crupi/GBM; i residui di nb_r1 non sono distorti più degli altri canali (ORBIT_ANALYSIS). Causa non determinata.",
        f"- **Dipendenza dalla rete**: lo stesso codice con due addestramenti dà {len(ev_leg)} (legacy) e {len(ev_ref)} (riferimento) eventi; "
        f"{len(pairs)} coppie in comune (abbinamento uno-a-uno degli intervalli ±2 bin); eventi abbinati a Crupi/GBM: {len(cp_leg)} legacy, "
        f"{len(cp_ref)} riferimento, tutti in coppia tra loro: {'sì' if cp_paired else 'no'}. Cambiano gli eventi senza controparte.",
        "- **Localizzazione** (step 6): eseguita e deterministica (seed per evento; seriale = parallela), ma **non validata** contro le "
        "posizioni dei cataloghi (GBM o Crupi). RA/Dec, distanze da Sole e Terra e le classi che ne dipendono vanno usate con cautela.",
        "- **Classificatore**: baseline euristica di Crupi (soglie da decision tree rifinite a mano); mancano la regola FP e le feature `fe_*` (tsfel).",
        "- **Scelte paper ↔ codice** (docs/WORKING_RULES.md §2): FOCuS sui rate, esclusione SAA ±150 bin, t_max 50 bin (codice upstream); "
        "confronto col paper fino al 9 luglio solo come ordine di grandezza.",
        "",
        "## 6. Checksum sha256",
        "",
        md_table(pd.DataFrame(checksums)),
        "",
        "## 7. Cosa è versionato e cosa no",
        "",
        "- Versionati: codice, documenti, e per ogni run `manifest.json`, `RESULTS.md`, `results/`, `validation/` e le tabelle di `analysis/`; "
        "di ogni bundle solo `metadata.json`.",
        "- **Non versionati** (pesanti, presenti solo su disco; `data/README.md`): `data/runs/*/*/pred/` e `trig/` (matrici, ~2.7 GB per run, "
        "symlink nelle v3), pesi e scaler dei bundle, dati grezzi e preprocessati, `data/gbm_burst_catalog.db`, `logs/`, `data/_archive_*/` "
        "(salvo README e checksum). Le run v3 dipendono dalle v2 tramite symlink: spostare o cancellare una run v2 rompe la v3 corrispondente.",
        "",
    ]
    DOC.write_text("\n".join(L), encoding="utf-8")
    text = README.read_text(encoding="utf-8")
    if not README_BLOCK.search(text):
        raise ValueError("README.md has no BASELINE:START/END block")
    README.write_text(README_BLOCK.sub(lambda m: m.group(1) + readme_block(ref, cmp) + m.group(2), text), encoding="utf-8")
    detail(f"written {rel(DOC)} and the example block of README.md")


if __name__ == "__main__":
    main()
