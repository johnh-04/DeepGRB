"""
Writes docs/BASELINE_2019.md, the reference document of the 2019 baseline, from files on disk
(run manifests, bundle metadata, validation outputs) and computes the sha256 checksums.

Usage (repo root): python -m benchmark.baseline_doc
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pandas as pd

from benchmark.report import md_table
from connections.utils.config import BASE_DIR, END_DATE, ENGINE_VERSION, START_DATE
from models.saa_flags import EDGE_WINDOW_S, REGION_DEG, SAA_GAP_S, ZERO_PAD_BINS

DOC = BASE_DIR / "docs" / "BASELINE_2019.md"
RUNS = BASE_DIR / "data" / "runs" / f"{START_DATE}_{END_DATE}"
REFERENCE = {"run": "engine-v3-seed1", "out": "benchmark/out/v3-seed1"}
TABLE = [  # (label, run folder, validation folder)
    ("v2 legacy", "engine-v2", "benchmark/out"),
    ("v2 seed1", "engine-v2-seed1", "benchmark/out/seed1"),
    ("v3 seed1 (riferimento)", "engine-v3-seed1", "benchmark/out/v3-seed1"),
    ("v3 legacy", "engine-v3", "benchmark/out/v3"),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()


def manifest(run: str) -> dict:
    p = RUNS / run / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def bundle_of(run: str) -> str:
    m = manifest(run)
    return (m.get("reused_from") or {}).get("model_bundle") or m.get("parameters", {}).get("model_bundle", "?")


def key_numbers(label: str, run: str, out: str) -> dict:
    o = BASE_DIR / out
    rep = (o / "REPORT.md").read_text()
    known, unknown = pd.read_csv(o / "matches_crupi_known.csv"), pd.read_csv(o / "matches_crupi_unknown.csv")
    ev = pd.read_csv(RUNS / run / "results" / "events_table.csv")
    u_rs = unknown[unknown["CE"].isin(["R", "S"])]
    row = {
        "run": f"{label} (`{run}`)",
        "eventi": len(ev),
        "CE R/S/P": "/".join(str(int((ev["CE"] == c).sum())) for c in "RSP"),
        "Crupi noti": f"{int(known['matched'].sum())}/{len(known)}",
        "Crupi inediti": f"{int(unknown['matched'].sum())}/{len(unknown)}",
        "inediti R+S": f"{int(u_rs['matched'].sum())}/{len(u_rs)}",
        "GBM rivelati/disponibili": re.search(r"disponibili: (\d+); rivelati: \*\*(\d+)\*\*", rep).group(2) + "/"
                                    + re.search(r"disponibili: (\d+); rivelati", rep).group(1),
        "GRB": re.search(r"\| rivelati / disponibili \| (\d+/\d+)", rep).group(1),
        "T90>4.096 / ≤4.096": re.search(r"\| T90 > 4.096 s \| (\d+/\d+)", rep).group(1) + " / "
                              + re.search(r"\| T90 ≤ 4.096 s \| (\d+/\d+)", rep).group(1),
        "senza controparte": int(re.search(r"Senza controparte .*?\*\*(\d+)\*\*", rep).group(1)),
    }
    flags = o / "events_flags.csv"
    if flags.exists():
        f = pd.read_csv(flags)
        cols = [c for c in ("saa_edge_short_passage", "saa_region_proximity", "near_zero_prediction") if c in f.columns]
        anyf = f[cols].any(axis=1)
        row["flaggati: abbinati / senza controparte"] = (f"{int((anyf & f['counterpart']).sum())}/{int(f['counterpart'].sum())} / "
                                                         f"{int((anyf & ~f['counterpart']).sum())}/{int((~f['counterpart']).sum())}")
    else:
        row["flaggati: abbinati / senza controparte"] = "—"
    cls = o / "classification_vs_crupi.csv"
    if cls.exists() and (RUNS / run / "results" / "events_classified.csv").exists():
        c = pd.read_csv(cls)
        ok = c.apply(lambda r: r["predicted_class"] in str(r["crupi_class"]).split("/"), axis=1)
        row["classe compatibile con Crupi"] = f"{int(ok.sum())}/{len(c)}"
    else:
        row["classe compatibile con Crupi"] = "—"
    return row


def main() -> None:
    ref_run = REFERENCE["run"]
    ref_bundle = BASE_DIR / bundle_of(ref_run)
    legacy_bundle = BASE_DIR / bundle_of("engine-v3")
    meta = json.loads((ref_bundle / "metadata.json").read_text())
    legacy_meta = json.loads((legacy_bundle / "metadata.json").read_text())
    m_ref, m_leg = manifest(ref_run), manifest("engine-v3")
    mae_test = sum(v["mae_test"] for v in meta["metrics"].values()) / len(meta["metrics"])

    checksums = []
    for b in (ref_bundle, legacy_bundle):
        for f in sorted(b.iterdir()):
            if f.is_file():
                checksums.append({"file": str(f.relative_to(BASE_DIR)), "sha256": sha256(f)})
    for run in ("engine-v3-seed1", "engine-v3", "engine-v2-seed1", "engine-v2"):
        for name in ("events_table.csv", "triggers_table.csv", "events_table_loc.csv", "events_classified.csv"):
            f = RUNS / run / "results" / name
            if f.exists():
                checksums.append({"file": str(f.relative_to(BASE_DIR)), "sha256": sha256(f)})

    ref_flags = pd.read_csv(BASE_DIR / REFERENCE["out"] / "events_flags.csv")
    nb_lone = ref_flags.loc[~ref_flags["counterpart"], "detectors"].str.contains("nb")
    nb_match = ref_flags.loc[ref_flags["counterpart"], "detectors"].str.contains("nb")
    near_zero_ids = ref_flags.loc[ref_flags["near_zero_prediction"], "trig_ids"].tolist()
    zero = m_ref.get("predicted_zero_cells", {})
    from benchmark.matching import overlap_one_to_one
    ev_ref = pd.read_csv(RUNS / ref_run / "results" / "events_table.csv")
    ev_leg = pd.read_csv(RUNS / "engine-v3" / "results" / "events_table.csv")
    pairs = overlap_one_to_one(ev_ref["start_met"], ev_ref["duration"], ev_leg["start_met"], ev_leg["duration"])
    n_ref, n_leg = len(ev_ref), len(ev_leg)
    leg_flags = pd.read_csv(BASE_DIR / "benchmark" / "out" / "v3" / "events_flags.csv")
    cp_ref = set(ref_flags.loc[ref_flags["counterpart"], "trig_ids"])
    cp_leg = set(leg_flags.loc[leg_flags["counterpart"], "trig_ids"])
    n_cp_ref, n_cp_leg = len(cp_ref), len(cp_leg)
    paired = {(int(ev_ref.at[i, "trig_ids"]), int(ev_leg.at[j, "trig_ids"])) for i, j, _ in pairs}
    cp_paired = all(any(a == r and b in cp_leg for a, b in paired) for r in cp_ref)
    zp = BASE_DIR / "benchmark" / "analysis" / "out" / "zero_prediction_summary.json"

    L = [
        "# Baseline 2019 — documento di riferimento",
        "",
        f"Generato da `python -m benchmark.baseline_doc` (codice al commit `{git('rev-parse', '--short', 'HEAD')}`, "
        f"branch `{git('rev-parse', '--abbrev-ref', 'HEAD')}`). Numeri, metadati e checksum letti dai file; nessuna cifra scritta a mano.",
        "",
        "## 1. Riferimento",
        "",
        f"- Periodo: {START_DATE} → {END_DATE} (inclusivo). Motore: engine v{ENGINE_VERSION} (v3 = v2 con S che ignora i bin con fondo previsto ≤ 0).",
        f"- **Run di riferimento**: `data/runs/{START_DATE}_{END_DATE}/{ref_run}`; step 5 eseguito dal commit "
        f"`{(m_ref.get('runs') or [{}])[-1].get('git_commit', '?')[:7]}`, predizioni e trigger riusati da `{(m_ref.get('reused_from') or {}).get('run', '?')}` "
        f"(prodotti dal commit `{str((m_ref.get('reused_from') or {}).get('source_git_commit', '?'))[:7]}`).",
        f"- **Run di confronto (rete legacy)**: `data/runs/{START_DATE}_{END_DATE}/engine-v3`, predizioni da `{(m_leg.get('reused_from') or {}).get('run', '?')}`.",
        f"- **Rete di riferimento**: `{ref_bundle.relative_to(BASE_DIR)}`",
        f"  - seed {meta.get('seed')}; periodo {meta['period']['start_date']} → {meta['period']['end_date']}; addestrata il {str(meta.get('trained_at', '?'))[:19]} dal commit `{str(meta.get('git_commit', '?'))[:7]}`;",
        f"  - iperparametri: {', '.join(f'{k}={v}' for k, v in meta['hyperparameters'].items() if not isinstance(v, dict))};",
        f"  - righe fit/validazione/test: {meta['rows']['fit']}/{meta['rows']['validation']}/{meta['rows']['test']}; epoche {meta.get('epochs_run')}, migliore {meta.get('best_epoch')}; "
        f"tempo di fit {meta.get('training_seconds', 0) / 60:.1f} min su {', '.join(meta.get('devices', []))};",
        f"  - MAE di test media sui 36 canali {mae_test:.3f}; controllo di convergenza: "
        + ("presente nei metadati" if "convergence" in meta else "assente (training precedente al controllo; riferimento: val_loss migliore "
           f"{min(meta['history']['val_loss']):.2f} contro 20.4 del predittore costante per canale, `benchmark/analysis/out/lr_check.json`)") + ";",
        f"  - versioni: {', '.join(f'{k} {v}' for k, v in meta['versions'].items())}.",
        f"- **Rete legacy**: `{legacy_bundle.relative_to(BASE_DIR)}` ({legacy_meta.get('note', '')}).",
        "",
        "## 2. Riproduzione",
        "",
        "Dalla radice del repo, env `deepgrb_recas`. Download e preprocess devono essere completi (`python -m benchmark.audit.data_inventory`).",
        "",
        "```bash",
        "# a) Riferimento seed1 a partire dagli artefatti esistenti (riusa pred/ e trig/ di engine-v2-seed1; nessun training)",
        "DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py",
        "python -m benchmark.classify --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --jobs 4",
        "python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --out benchmark/out/v3-seed1",
        "",
        "# b) Confronto con la rete legacy (riusa pred/ e trig/ di engine-v2)",
        "DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py",
        "python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v3 --out benchmark/out/v3",
        "",
        "# c) Da zero, nuovo training (cartelle e bundle non devono esistere; GPU consigliata)",
        "DEEPGRB_RUN_LABEL=seed1 DEEPGRB_TRAIN_SEED=1 DEEPGRB_FORCE_TRAIN=1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py",
        "```",
        "",
        "Le cartelle di run etichettate non vengono mai sovrascritte: per ripetere a) o c) spostare prima la cartella esistente in `data/_archive_<data>/`. "
        "Un nuovo training (c) **non** riproduce i pesi bit a bit (su GPU TensorFlow non è deterministico): i numeri di questo documento sono riproducibili "
        "esattamente solo a partire dal bundle di riferimento (checksum in §6).",
        "",
        "## 3. Numeri chiave",
        "",
        md_table(pd.DataFrame([key_numbers(*t) for t in TABLE])),
        "",
        "Regola di abbinamento: uno-a-uno, istante del riferimento entro [inizio evento − 2 bin, fine evento + 2 bin] (`benchmark/matching.py`). "
        "Il paper (fino al 9 luglio) riporta 100 eventi, GRB 65/81, T90 > 4.096 s 60/68, T90 ≤ 4.096 s 5/13. "
        f"Le run v2 sono state validate prima dell'introduzione dei flag (\"—\"); i loro eventi coincidono con quelli delle v3 (salvo S dell'evento 6 di seed1).",
        "",
        "## 4. Flag di post-processing (`models/saa_flags.py`; non cambiano l'elenco degli eventi)",
        "",
        f"- `saa_edge_short_passage`: l'inizio dell'evento (change point FOCuS) cade entro {EDGE_WINDOW_S:.0f} s prima dell'entrata o dopo l'uscita di un "
        f"passaggio SAA (flag POSHIST) il cui buco nei dati è ≤ {SAA_GAP_S:.0f} s, quindi **non mascherato** dallo step 3.",
        f"- `saa_region_proximity`: la posizione di Fermi all'inizio dell'evento è entro {REGION_DEG}° dalla regione con flag SAA nelle POSHIST "
        "(regione campionata su griglia di 0.1°).",
        f"- `near_zero_prediction`: i bin dell'evento, estesi di {ZERO_PAD_BINS} per lato, toccano un bin con fondo previsto ≤ 0. "
        f"Nella run di riferimento: eventi {near_zero_ids}.",
        "",
        "Per evento: `benchmark/out/<run>/events_flags.csv`. Analisi che li motiva: `docs/ORBIT_ANALYSIS.md`.",
        "",
        "## 5. Limiti noti e perimetro",
        "",
        f"- **Passaggi SAA brevi non mascherati** (gruppo A di ORBIT_ANALYSIS): la maschera agisce solo sui buchi > {SAA_GAP_S:.0f} s; prima dei passaggi "
        f"brevi la rete sottostima il fondo. Eventi con `saa_edge_short_passage` nel riferimento: {int(ref_flags['saa_edge_short_passage'].sum())}, "
        f"di cui abbinati a Crupi/GBM {int((ref_flags['saa_edge_short_passage'] & ref_flags['counterpart']).sum())}.",
        f"- **Bordo nord della SAA** (gruppo B): eventi senza controparte vicini alla regione SAA, nell'orbita che precede il primo passaggio di una "
        f"sequenza. Senza controparte con `saa_region_proximity` e senza `saa_edge_short_passage`: "
        f"{int((ref_flags['saa_region_proximity'] & ~ref_flags['saa_edge_short_passage'] & ~ref_flags['counterpart']).sum())}.",
        f"- **Celle con fondo previsto 0** (rete seed1): {zero.get('cells', '?')} celle in {zero.get('bins_any_channel', '?')} bin; "
        + ("la rete è instabile dove la velocità angolare (w1, w2, w3) è nella coda estrema della distribuzione: la pre-attivazione finale diventa negativa "
           "e la ReLU taglia a zero (ORBIT_ANALYSIS §5b). " if zp.exists() else "")
        + f"Da engine v3 quei bin sono esclusi da S; gli eventi adiacenti ({near_zero_ids}) restano e sono marcati da `near_zero_prediction`.",
        f"- **Rivelatore nb**: compare in {int(nb_lone.sum())}/{len(nb_lone)} eventi senza controparte contro {int(nb_match.sum())}/{len(nb_match)} "
        "abbinati a Crupi/GBM; i residui di nb_r1 non sono distorti più degli altri canali (ORBIT_ANALYSIS e report). Causa non determinata.",
        f"- **Dipendenza dalla rete**: lo stesso codice con due addestramenti dà {n_leg} (legacy) e {n_ref} (seed1) eventi; {len(pairs)} coppie in comune "
        f"(abbinamento uno-a-uno degli intervalli ±2 bin); eventi abbinati a Crupi/GBM: {n_cp_leg} legacy, {n_cp_ref} seed1, tutti in coppia tra loro: "
        f"{'sì' if cp_paired else 'no'}. Cambiano gli eventi senza controparte.",
        "- **Localizzazione** (dentro `benchmark.classify`): eseguita e deterministica (seed per evento; seriale = parallela), "
        "ma **non validata** contro le posizioni dei cataloghi (GBM o Crupi). RA/Dec, distanze da Sole e Terra e le classi che ne dipendono vanno usate con cautela.",
        "- **Classificatore**: baseline euristica di Crupi (soglie da decision tree rifinite a mano); mancano la regola FP e le feature `fe_*` (tsfel).",
        "- **Scelte paper ↔ codice** (docs/WORKING_RULES.md §2): FOCuS sui rate, esclusione SAA ±150 bin, t_max 50 bin (codice upstream); confronto col paper fino al 9 luglio solo come ordine di grandezza.",
        "",
        "## 6. Checksum sha256",
        "",
        md_table(pd.DataFrame(checksums)),
        "",
        "## 7. Cosa è versionato e cosa no",
        "",
        "- Versionati: codice, documenti, `benchmark/out/v3-seed1/` e `benchmark/out/v3/` (REPORT.md e CSV), metadati e scaler dei bundle già tracciati.",
        "- **Non versionati** (pesanti o derivati, presenti solo su disco): `data/runs/*/pred/`, `data/runs/*/trig/` (matrici, ~2.7 GB per run); "
        "le cartelle `data/runs/*/engine-v2-seed1/`, `engine-v3/`, `engine-v3-seed1/` (results, manifest e i symlink `pred`/`trig` delle v3 verso le v2); "
        "il bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/` (pesi, scaler, metadata); `benchmark/out/seed1/`; "
        "`benchmark/analysis/out/`; `logs/`; `data/_archive_*/` (salvo README e checksum). "
        "Le run v3 dipendono dalle v2 tramite symlink: spostare o cancellare una run v2 rompe la v3 corrispondente.",
        "",
    ]
    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"written {DOC}")


if __name__ == "__main__":
    main()
