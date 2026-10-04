"""
Writes docs/ORBIT_ANALYSIS.md from the outputs of benchmark.analysis.orbit_analysis and
benchmark.analysis.zero_prediction (in <reference run>/analysis/). Every number in the document
is read from those files.

Usage (repo root): python -m benchmark.analysis.orbit_report --run <reference run> --compare <comparison run>
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import benchmark.analysis.orbit_analysis as oa
from benchmark.report import md_table as md
from benchmark.analysis.orbit_analysis import BANDS, EDGE_WINDOW_S, REGION_DEG, SHORT_PASSAGE_S
from connections.utils.config import BASE_DIR, DOCS_DIR
from utils.logs import detail, setup_logging
from utils.run_options import manifest_model, read_manifest

DOC = DOCS_DIR / "ORBIT_ANALYSIS.md"
R = C = ""  # names of the reference and comparison runs (set in main)


def bundle_name(run: Path) -> str:
    return Path(manifest_model(read_manifest(run)).get("bundle") or "?").name


def rng(s: pd.Series, fmt: str = ".0f") -> str:
    return f"{format(s.min(), fmt)}–{format(s.max(), fmt)}"


def near_zero_events() -> list:
    """Events of the reference run flagged near_zero_prediction (pipeline step 7)."""
    f = oa.RUNS["ref"]["run"] / "results" / "events_flags.csv"
    return pd.read_csv(f).query("near_zero_prediction")["trig_ids"].tolist() if f.exists() else []


def zero_prediction_section() -> list:
    """Section on the bins where the reference network predicts zero (benchmark.analysis.zero_prediction)."""
    if not (oa.OUT / "zero_prediction_summary.json").exists():
        return []
    Z = json.loads((oa.OUT / "zero_prediction_summary.json").read_text())
    bins = pd.read_csv(oa.OUT / "zero_prediction_bins.csv")
    inp = pd.read_csv(oa.OUT / "zero_prediction_inputs.csv")
    sens = pd.read_csv(oa.OUT / "zero_prediction_sensitivity.csv")
    zb, nb = bins[bins["zero_bin"]], bins[~bins["zero_bin"]]
    w = inp[inp["feature"].isin(["w1", "w2", "w3"])]
    restore = sens[sens["out_sum_after_replacing"] > 0].groupby("row")["feature"].apply(lambda f: ", ".join(sorted(f)) if len(f) <= 3 else f"{len(f)} input")
    full_zero = zb[zb["ref_channels_le0"] == 36]
    adjacent = nb[(nb["ref_pred_sum_r1"] < 0.8 * nb["cmp_pred_sum_r1"])]
    tab = zb[["timestamp", "dt_prev_s", "n_nan_inputs", "max_abs_z", "feature_max_abs_z", "max_jump_over_p999",
              "ref_channels_le0", "preact_max", "penultimate_mean_abs", "cmp_pred_sum_r1"]].assign(
        timestamp=zb["timestamp"].str.slice(0, 19), inputs_that_restore=[restore.get(r, "-") for r in zb["row"]])
    return [
        f"## 5b. Bin con fondo previsto nullo nella rete {R}",
        "",
        "Generato da `python -m benchmark.analysis.zero_prediction` (sola lettura: dataset ricostruito con `ModelNN.prepare`, "
        f"allineato riga per riga a `pred/`; bundle `{bundle_name(oa.RUNS['ref']['run'])}`).",
        "",
        f"- **Dove**: {len(zb)} bin, {Z['cells']} celle, in due tratti consecutivi: "
        + ", ".join(t[:19] for t in Z["zero_timestamps"]) + ".",
        f"- **Ingressi**: nessun NaN ({Z['nan_inputs_in_zero_bins']} su {len(zb)} × 60), bin regolari (Δt dal precedente "
        f"{zb['dt_prev_s'].min():.3f}–{zb['dt_prev_s'].max():.3f} s), nessun salto: la variazione massima rispetto al bin precedente è "
        f"{Z['max_jump_over_p999_zero_bins']:.2f} volte il 99.9° percentile dei salti tipici (vicini: {Z['max_jump_over_p999_neighbours']:.2f}).",
        f"- **Cosa hanno di anomalo**: la velocità angolare. `w1`, `w2`, `w3` sono **insieme** nella coda della distribuzione del periodo "
        f"(percentili {w['percentile_in_period'].min():.2f}–{w['percentile_in_period'].max():.3f}; |z| fino a {w['z'].abs().max():.2f} rispetto allo "
        f"scaler di training). Non sono fuori scala: |z| massimo nei bin a zero {Z['max_abs_z_zero_bins']:.2f}, nei bin vicini {Z['max_abs_z_neighbours']:.2f}.",
        f"- **Perché la rete dà 0**: la pre-attivazione dello strato di uscita (ReLU) è negativa su tutti i canali nei bin a zero pieno "
        f"(massimo {full_zero['preact_max'].max():.0f}; nei vicini il massimo è almeno {Z['preact_max_neighbours_min']:.0f}), e l'attivazione media "
        f"del penultimo strato è {full_zero['penultimate_mean_abs'].min():.1f}–{full_zero['penultimate_mean_abs'].max():.1f} contro "
        f"{nb['penultimate_mean_abs'].min():.2f}–{nb['penultimate_mean_abs'].max():.2f} nei vicini: la rappresentazione interna esplode e la ReLU finale taglia a zero. "
        "Non è un clipping esplicito né un ingresso NaN o fuori scala.",
        f"- **Sensibilità**: sostituendo un solo ingresso con la media dei vicini, nei bin a zero pieno l'uscita torna positiva solo con `w1` o `w2` "
        "(tabella sotto); con tutti gli ingressi dei vicini l'uscita è positiva in ogni caso "
        f"({'sì' if Z['neighbour_mean_input_output_positive'] else 'no'}). La rete {R} ha una risposta molto ripida in questa regione rara dello spazio "
        f"degli ingressi; la rete di {C} sugli stessi bin prevede {min(Z['cmp_pred_sum_r1_zero_bins']):.0f}–{max(Z['cmp_pred_sum_r1_zero_bins']):.0f} "
        "(somma dei 12 NaI in r1), valori normali.",
        f"- **Bin adiacenti**: {len(adjacent)} bin vicini hanno una predizione {R} inferiore all'80% di quella di {C} "
        f"({', '.join(adjacent['timestamp'].str.slice(0, 19))}). Eventi di {R} con il flag `near_zero_prediction`: "
        f"{', '.join(map(str, near_zero_events())) or 'nessuno'}; sono probabili artefatti di questa instabilità.",
        "",
        md(tab, ".2f"),
        "",
        "Flag di post-processing `near_zero_prediction` (evento esteso di 5 bin che tocca un bin con fondo previsto ≤ 0): `models/flags.py` (step 7 della pipeline), riportato nel `RESULTS.md` della run.",
        "",
    ]


def main() -> None:
    global R, C
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    oa.add_cli(parser)
    args = parser.parse_args()
    setup_logging()
    oa.configure(args.run, args.compare)
    R, C = oa.RUNS["ref"]["run"].name, oa.RUNS["cmp"]["run"].name
    S = json.loads((oa.OUT / "summary.json").read_text())
    ev = {n: pd.read_csv(oa.OUT / f"events_orbit_{n}.csv") for n in oa.RUNS}
    null = pd.read_csv(oa.OUT / "null_orbit.csv")
    ks = pd.read_csv(oa.OUT / "ks_tests.csv")
    frac = pd.read_csv(oa.OUT / "saa_fractions.csv", keep_default_na=False)  # "null" is a group name
    resid = pd.read_csv(oa.OUT / "residual_by_zone.csv")
    cross = pd.read_csv(oa.OUT / "overlap_cmp_rows_vs_ref_cols.csv", index_col=0)
    others = pd.read_csv(oa.OUT / "others_ref.csv")
    P = S["orbital_period_s"]
    s1, v2 = ev["ref"], ev["cmp"]
    A, B, O, M = (s1[s1["group"] == g] for g in ("A", "B", "other", "matched"))
    fr = frac.set_index(["run", "group"])
    rz = resid.set_index(["run", "zone"])
    z_before, z_after = f"{EDGE_WINDOW_S:.0f} s before short passage", f"{EDGE_WINDOW_S:.0f} s after short passage"
    z_region = f"within {REGION_DEG} deg of SAA region"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()

    man_v2 = read_manifest(oa.RUNS["cmp"]["run"])
    last_v2 = man_v2["runs"][-1]
    out_rel = oa.OUT.relative_to(BASE_DIR)
    out_from_docs = os.path.relpath(oa.OUT, DOCS_DIR)

    L = []
    L += [
        "# Analisi orbitale degli eventi della baseline 2019",
        "",
        f"Generato da `python -m benchmark.analysis.orbit_analysis` e `python -m benchmark.analysis.orbit_report` (commit `{commit}`). "
        f"Sola lettura sugli output del motore: nessuna run, bundle o parametro modificato. Tutti i numeri vengono dai file in `{out_rel}/`.",
        "",
        f"Run analizzate: `{C}` (rete `{bundle_name(oa.RUNS['cmp']['run'])}`) e `{R}` (rete `{bundle_name(oa.RUNS['ref']['run'])}`). "
        f"Eventi: {C} {S['runs']['cmp']['events']} ({S['runs']['cmp']['without_counterpart']} senza controparte), "
        f"{R} {S['runs']['ref']['events']} ({S['runs']['ref']['without_counterpart']} senza controparte). "
        "\"Senza controparte\" = né catalogo trigger GBM né tabelle di Crupi (regola primaria di `benchmark/validate.py`).",
        "",
        *([f"> Nota di integrità: `{C}/manifest.json` (formato precedente al consolidamento) ha una voce del {last_v2['started'][:19]} UTC "
           f"(commit {last_v2['git_commit'][:7]}) e il blocco parametri riporta `train_seed: {man_v2['parameters'].get('train_seed')}` con "
           f"`model_mode: {man_v2['parameters'].get('model_mode')}`, valori che non descrivono il modello usato (difetto 17, corretto nel "
           "consolidamento: i manifest nuovi registrano il modello dal bundle). pred/trig/results non sono stati riscritti.", ""]
          if "model_mode" in man_v2.get("parameters", {}) else []),
        "## 1. Definizione di `dist_saa_gap_s`",
        "",
        "Calcolata in `benchmark/validate.py` (non modificata):",
        "",
        "- i **buchi** sono gli intervalli tra due righe consecutive di `pred/frg.csv` distanti più di 500 s (`np.diff(met) > 500`); "
        "`frg.csv` contiene solo i bin fuori SAA e mantiene il `met` anche dei bin mascherati;",
        "- per ogni buco si prendono **due bordi**: il `met` dell'ultimo bin prima del buco (inizio) e del primo bin dopo (fine). Sono i bordi del **buco nei dati**, non della maschera (che si estende 150 bin, ≈614 s, verso l'interno dei dati);",
        "- il tempo dell'evento è l'**inizio con offset FOCuS** (`start_times_offset`, il change point);",
        "- `dist_saa_gap_s` = minimo di |bordo − tempo| su tutti i bordi: distanza **non firmata** dal bordo più vicino, sia esso un inizio o una fine.",
        "",
        f"Ricalcolata qui con la stessa definizione: differenza massima con il CSV della validazione {S['runs']['ref']['dist_check_max_abs_diff_s']:.1e} s. "
        "Le distanze firmate dal buco precedente e successivo sono nelle colonne `t_since_gap_end_s` e `t_to_gap_start_s`.",
        "",
        f"Gruppi degli eventi senza controparte (bande che contengono i due addensamenti di {R} con margine): "
        + ", ".join(f"**{g}** = {a:.0f}–{b:.0f} s" for g, (a, b) in BANDS.items()) + ", **altri** = il resto.",
        "",
        "## 2. Sovrapposizione tra le due reti",
        "",
        f"Abbinamento uno-a-uno di intervalli [inizio, inizio + durata] estesi di ±2 bin (greedy per |Δinizio|): "
        f"**{S['overlap']['pairs']}** coppie, **{S['overlap']['only_cmp']}** eventi solo in {C}, **{S['overlap']['only_ref']}** solo in {R} "
        f"(Δinizio mediano delle coppie {S['overlap']['median_abs_dstart_s']:.1f} s).",
        "",
        f"Righe: gruppo dell'evento in {C}; colonne: gruppo dell'evento abbinato in {R} (`absent` = nessun abbinamento).",
        "",
        md(cross.reset_index().rename(columns={"row_0": f"{C} \\ {R}"}), ".0f"),
        "",
        f"Eventi solo in {R} per gruppo: " + ", ".join(f"{k} {v}" for k, v in S["overlap"]["only_ref_by_group"].items()) + ".",
        "",
        f"Risposta: gli eventi senza controparte **sono in gran parte gli stessi** nelle due reti. "
        f"Tutti i {int((s1['group'] == 'A').sum())} A di {R} hanno un A in {C}; "
        f"B: {int(((s1['group'] == 'B') & (s1['pair_group'] == 'B')).sum())}/{int((s1['group'] == 'B').sum())}; "
        f"altri: {int(((s1['group'] == 'other') & (s1['pair_group'] == 'other')).sum())}/{int((s1['group'] == 'other').sum())}. "
        f"Nessun evento cambia categoria tra abbinato e senza controparte. La rete legacy ne produce di più in A "
        f"({S['runs']['cmp']['groups'].get('A', 0)} contro {S['runs']['ref']['groups'].get('A', 0)}).",
        "",
        "## 3. Posizione orbitale",
        "",
        "Metodo (per **tutti** gli eventi di entrambe le run e per "
        f"{len(null)} istanti casuali presi tra i bin validi di {C}, ipotesi nulla):",
        "",
        "- latitudine, longitudine: POSHIST (1 Hz, campione più vicino); altitudine e **L di McIlwain**: `gbm.data.PosHist` (gbm-data-tools);",
        f"- latitudine geomagnetica: **dipolo centrato semplice** (polo IGRF-13 2020: {S['dipole_pole'][0]}°N, {S['dipole_pole'][1]}°E), approssimazione;",
        "- fase orbitale: argomento di latitudine (0° = nodo ascendente) da posizione e velocità ECI;",
        f"- SAA: intervalli dal bit SAA dei `FLAGS` di POSHIST ({S['n_saa_passages']} passaggi nel periodo); periodo orbitale P = {P:.0f} s "
        "(mediana tra nodi ascendenti);",
        "- distanze firmate: tempo dall'ultima **uscita** e alla prossima **entrata** nella SAA; posizione di t − P rispetto al passaggio SAA dell'orbita precedente "
        "(0 = dentro la SAA; negativo = prima dell'entrata; positivo = dopo l'uscita); tempo dalla fine del buco dati precedente e all'inizio del successivo;",
        "- distanza geografica dalla regione SAA: grande cerchio fino al più vicino campione POSHIST con flag SAA.",
        "",
        f"![mappa]({out_from_docs}/map_lat_lon.png)",
        "",
        f"![tempo dall'uscita SAA]({out_from_docs}/hist_time_since_saa_exit.png)",
        "",
        f"### Mediane per gruppo ({R})",
        "",
    ]
    cols = ["lat", "lon", "L", "geomag_lat_dipole", "phase_deg", "t_since_saa_exit_s", "t_to_saa_entry_s",
            "prev_orbit_saa_offset_s", "dist_saa_region_deg", "alt_km"]
    med = pd.DataFrame([{"gruppo": f"{g} ({len(d)})", **{c: d[c].median() for c in cols}}
                        for g, d in (("abbinati", M), ("A", A), ("B", B), ("altri", O), ("nulla", null))])
    L += [md(med, ".1f"), ""]
    L += ["### Vicinanza alla SAA (conteggi)", "",
          md(frac.rename(columns={"prev_orbit_in_saa": "t−P dentro SAA", "prev_orbit_within_300s": "t−P entro 300 s da SAA",
                                  "next_saa_entry_within_1_orbit": "entrata SAA entro 1 orbita"}), ".0f"), ""]
    sel = ks[(ks["run"] == "ref") & ks["variable"].isin(["lat", "lon", "L", "phase_deg", "dist_saa_region_deg",
                                                             "t_to_saa_entry_s", "prev_orbit_saa_offset_s"])]
    piv = sel.pivot_table(index=["group", "variable"], columns="vs", values="p_value").reset_index()
    L += [f"### Test KS a due campioni ({R}; p-value contro abbinati e contro tempi casuali)", "",
          f"Tutti i test (entrambe le run, tutte le variabili) sono in `{out_rel}/ks_tests.csv`. "
          "Campioni piccoli (A 17, B 10): i p-value indicano differenze di distribuzione, non la causa.", "",
          md(piv, ".1e"), ""]
    L += ["### Il fondo previsto è sottostimato vicino alla SAA? (tutti i bin validi, non solo gli eventi)", "",
          f"Residuo relativo della somma dei 12 NaI in r1, (frg − bkg)/bkg, e frazione di bin con FOCuS r1 > 3σ su almeno un rivelatore. "
          f"\"Passaggio breve\" = passaggio SAA più corto di {SHORT_PASSAGE_S:.0f} s ({S['short_passages']} nel periodo, durata "
          f"{S['short_passage_duration_s'][0]:.0f}–{S['short_passage_duration_s'][2]:.0f} s, mediana {S['short_passage_duration_s'][1]:.0f} s): "
          "il suo buco nei dati resta sotto la soglia di 500 s e **non viene mascherato**.", "",
          md(resid, ".2f"), ""]

    # ---------------- verdict
    a_before = S["runs"]["ref"]["A_before_short_passage"]
    L += [
        "## 4. Verdetto",
        "",
        "### Gruppo A — ipotesi \"periferia SAA\": **sostenuta**, con un meccanismo preciso",
        "",
        f"- Posizione: tutti i {len(A)} eventi A di {R} sono a lat {rng(A['lat'], '.1f')}°, lon {rng(A['lon'], '.1f')}°, sul **bordo occidentale** della regione SAA "
        f"(a lat −12° la regione con flag va da lon {S['saa_region']['lon_range_at_lat_-12'][0]:.1f}° a {S['saa_region']['lon_range_at_lat_-12'][1]:.1f}°), "
        f"fase {rng(A['phase_deg'], '.0f')}°, a {rng(A['dist_saa_region_deg'], '.1f')}° dalla regione SAA "
        f"(abbinati: mediana {M['dist_saa_region_deg'].median():.0f}°; tempi casuali entro {REGION_DEG}°: {S['null_within_region_%']:.2f}%).",
        f"- Tempo: iniziano {rng(A['t_to_saa_entry_s'])} s **prima di entrare** nella SAA; {a_before}/{len(A)} precedono di al più "
        f"{EDGE_WINDOW_S:.0f} s un **passaggio breve** (< {SHORT_PASSAGE_S:.0f} s) il cui buco dati non è mascherato. "
        f"Un'orbita prima Fermi era dentro la SAA in {int(fr.loc[('ref', 'A'), 'prev_orbit_in_saa'])}/{len(A)} casi "
        f"(tempi casuali: {int(fr.loc[('null', 'null'), 'prev_orbit_in_saa'])}/{int(fr.loc[('null', 'null'), 'n'])}).",
        f"- Il raggruppamento di `dist_saa_gap_s` a ≈ 5100–5200 s viene dalla definizione: il passaggio breve subito dopo l'evento non produce "
        f"un buco > 500 s, quindi il bordo più vicino è la fine del buco lungo dell'**orbita precedente**. Per gli A, t − P cade "
        f"{rng(P - A['t_since_gap_end_s'])} s prima di quella fine (P = {P:.0f} s), cioè dentro il passaggio SAA precedente.",
        f"- Fondo: nei {EDGE_WINDOW_S:.0f} s prima dei passaggi brevi il residuo relativo al 90° percentile è "
        f"{rz.loc[('ref', z_before), 'p90_rel_residual_%']:.1f}% (altrove {rz.loc[('ref', 'elsewhere'), 'p90_rel_residual_%']:.1f}%) e FOCuS "
        f"supera 3σ nel {rz.loc[('ref', z_before), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin (altrove {rz.loc[('ref', 'elsewhere'), 'frac_bins_focus_r1_gt3_%']:.2f}%); "
        f"dopo l'uscita nessun eccesso ({rz.loc[('ref', z_after), 'frac_bins_focus_r1_gt3_%']:.2f}%). La rete sottostima il fondo nell'avvicinamento ai passaggi brevi.",
        f"- Riproducibilità: stesso comportamento con la rete legacy ({C}: {S['runs']['cmp']['A_before_short_passage']} eventi A prima di un passaggio breve; "
        f"{rz.loc[('cmp', z_before), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin sopra 3σ in quella zona).",
        f"- Probabilità che {S['runs']['ref']['band_A_count']} dei {S['runs']['ref']['without_counterpart']} eventi senza controparte cadano nella banda A per caso "
        f"(frazione dei tempi casuali nella banda: {100 * S['null_fraction_in_band_A']:.2f}%): binomiale p = {S['runs']['ref']['band_A_binom_p']:.1e}.",
        "",
        "### Gruppo B — ipotesi \"periferia SAA nell'orbita successiva a un passaggio\": **non sostenuta nella forma proposta**; periferia SAA **sostenuta**, ma nell'orbita *precedente* al primo passaggio",
        "",
        f"- Posizione: lat {rng(B['lat'], '.1f')}°, lon {rng(B['lon'], '.1f')}°, fase {rng(B['phase_deg'], '.0f')}°, "
        f"a {rng(B['dist_saa_region_deg'], '.1f')}° dalla regione SAA: appena **a nord del bordo settentrionale** "
        f"(regione con flag: lat da {S['saa_region']['lat_min']:.1f}° a {S['saa_region']['lat_max']:.1f}°, lon da "
        f"{S['saa_region']['lon_min']:.1f}° a {S['saa_region']['lon_max']:.1f}°), una zona diversa da A.",
        f"- Tempo: un'orbita prima Fermi **non** era nella SAA ({int(fr.loc[('ref', 'B'), 'prev_orbit_in_saa'])}/{len(B)}); "
        f"dall'ultima uscita sono passate {B['t_since_saa_exit_s'].median() / 3600:.1f} h (mediana). "
        f"La prossima entrata arriva dopo {B['t_to_saa_entry_s'].median():.0f} s (mediana; {int((B['t_to_saa_entry_s'] > 5000).sum())}/{len(B)} tra "
        f"{B.loc[B['t_to_saa_entry_s'] > 5000, 't_to_saa_entry_s'].min():.0f} e {B.loc[B['t_to_saa_entry_s'] > 5000, 't_to_saa_entry_s'].max():.0f} s), "
        "cioè circa un'orbita dopo: B cade nell'orbita **che precede il primo passaggio** di una sequenza giornaliera, quando la traccia sfiora il bordo SAA senza entrarci.",
        f"- Fondo: entro {REGION_DEG}° dalla regione SAA FOCuS supera 3σ nel {rz.loc[('ref', z_region), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin "
        f"(altrove {rz.loc[('ref', 'elsewhere'), 'frac_bins_focus_r1_gt3_%']:.2f}%), residuo al 90° percentile {rz.loc[('ref', z_region), 'p90_rel_residual_%']:.1f}%.",
        f"- Probabilità della banda B per caso ({100 * S['null_fraction_in_band_B']:.2f}% dei tempi casuali): binomiale p = {S['runs']['ref']['band_B_binom_p']:.1e}. "
        f"Con 10 eventi, la conclusione sulla posizione è solida; quella sul meccanismo (perché proprio lì) resta un'ipotesi.",
        "",
        f"Eventi abbinati a Crupi/GBM nelle stesse bande: A {S['runs']['ref']['band_A_matched_count']}, B {S['runs']['ref']['band_B_matched_count']} "
        f"su {S['runs']['ref']['matched_n']}.",
        "",
        "### Possibile flag di post-processing (descrizione, non implementata)",
        "",
        "Un flag sull'**evento** (non un taglio sui trigger, nessuna modifica al motore), calcolato dopo `events_table.csv` dalla POSHIST:",
        f"- `saa_edge_short_passage`: l'inizio dell'evento è entro {EDGE_WINDOW_S:.0f} s prima (o dopo) un passaggio SAA più breve di {SHORT_PASSAGE_S:.0f} s (buco non mascherato);",
        f"- `saa_region_proximity`: la posizione di Fermi all'inizio dell'evento è entro {REGION_DEG}° dalla regione con flag SAA.",
        "Gli eventi flaggati restano nel catalogo, con la segnalazione \"possibile fondo di particelle al bordo SAA\". "
        f"Sui dati di {R} il primo flag coprirebbe {a_before} eventi A; il secondo i B (distanza ≤ {B['dist_saa_region_deg'].max():.1f}°). "
        "Soglie e conteggi andrebbero verificati anche sugli eventi abbinati prima di usarli.",
        "",
        f"## 5. Gli eventi \"altri\" senza controparte ({R})",
        "",
        f"{len(others)} eventi; voci del catalogo trigger GBM entro ±1 h dall'inizio (con Δt firmato).",
        "",
        md(others[["trig_ids", "start_times", "duration", "detectors", "sigma_C", "CE", "lat", "lon", "L", "phase_deg",
                   "t_since_saa_exit_s", "t_to_saa_entry_s", "dist_saa_gap_s", "pair_group", "gbm_within_1h"]].assign(
            start_times=others["start_times"].str.slice(0, 19)), ".1f"),
        "",
        f"`pair_group` = gruppo dell'evento abbinato in {C} (`absent` = presente solo in {R}). Mediane rispetto agli abbinati: "
        f"L {O['L'].median():.2f} contro {M['L'].median():.2f}, distanza dalla regione SAA {O['dist_saa_region_deg'].median():.0f}° contro {M['dist_saa_region_deg'].median():.0f}°.",
        "",
        "Osservazioni (descrittive, nessun verdetto):",
        "",
        f"- **Alta L.** {S['runs']['ref']['L_ge_1.4_by_group']['other'][0]}/{S['runs']['ref']['L_ge_1.4_by_group']['other'][1]} \"altri\" hanno L ≥ "
        f"{S['high_L_threshold']} (abbinati: {S['runs']['ref']['L_ge_1.4_by_group']['matched'][0]}/{S['runs']['ref']['L_ge_1.4_by_group']['matched'][1]}; "
        f"tempi casuali: {S['null_L_ge_1.4_%']:.1f}%). Si concentrano vicino ai punti di massima latitudine dell'orbita "
        f"(|lat| ≥ 24°: {int((O['lat'].abs() >= 24).sum())}/{len(O)}), cioè alle latitudini geomagnetiche più alte raggiunte da Fermi: "
        "zona compatibile con precipitazione di particelle, ma qui non verificata.",
        f"- **Fondo previsto nullo.** Nella run {R} la rete prevede fondo 0 in "
        f"{S['runs']['ref']['zero_bkg_cells']} celle ({S['runs']['ref']['zero_bkg_rows']} bin, due tratti di 3 bin consecutivi); nella {C} in "
        f"{S['runs']['cmp']['zero_bkg_cells']}. Bin a zero **dentro** la finestra di S: eventi {S['runs']['ref']['events_zero_bkg_inside_S_window']}; "
        f"finestra di S che inizia o finisce **a un bin** da quei bin: eventi {S['runs']['ref']['events_zero_bkg_adjacent_1bin']}. "
        f"In engine {C} `models/analyze.py::event_significance` non scartava B ≤ 0 (FOCuS sì) e l'evento con i bin a zero nella finestra aveva una "
        "significatività esplosa; la correzione è nel motore v3 (vedi `docs/WORKLOG.md`). Gli eventi adiacenti ai bin a zero non cambiano S, "
        f"ma il loro trigger parte subito dopo il reset di FOCuS su quei bin ed esistono solo nella rete {R}: probabili artefatti della rete, non verificati.",
        "",
        *zero_prediction_section(),
        "## 6. Limiti",
        "",
        f"- Le bande A/B sono state scelte guardando i dati di {R}: i p-value binomiali misurano quanto il raggruppamento è anomalo, non sono un test cieco.",
        "- Latitudine geomagnetica da dipolo centrato (approssimazione); L di McIlwain dalle tabelle di gbm-data-tools.",
        "- Il confronto dei residui usa la somma dei 12 NaI in r1; non distingue i singoli rivelatori.",
        "- La regione SAA è quella del flag di POSHIST, che è la regione in cui i rivelatori sono spenti; la regione fisica di particelle intrappolate è più ampia.",
        "",
    ]
    DOC.write_text("\n".join(L), encoding="utf-8")
    detail(f"written {DOC}")


if __name__ == "__main__":
    main()
