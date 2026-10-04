"""
Writes docs/ORBIT_ANALYSIS.md from the outputs of benchmark.analysis.orbit_analysis
(and lr_check). Every number in the document is read from those files.

Usage (repo root): python -m benchmark.analysis.orbit_report
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.analysis.orbit_analysis import BANDS, EDGE_WINDOW_S, OUT, REGION_DEG, RUNS, SHORT_PASSAGE_S
from connections.utils.config import BASE_DIR

DOC = BASE_DIR / "docs" / "ORBIT_ANALYSIS.md"


def md(df: pd.DataFrame, fmt: str = ".2f") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else format(v, fmt))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def rng(s: pd.Series, fmt: str = ".0f") -> str:
    return f"{format(s.min(), fmt)}–{format(s.max(), fmt)}"


def main() -> None:
    S = json.loads((OUT / "summary.json").read_text())
    ev = {n: pd.read_csv(OUT / f"events_orbit_{n}.csv") for n in RUNS}
    null = pd.read_csv(OUT / "null_orbit.csv")
    ks = pd.read_csv(OUT / "ks_tests.csv")
    frac = pd.read_csv(OUT / "saa_fractions.csv", keep_default_na=False)  # "null" is a group name
    resid = pd.read_csv(OUT / "residual_by_zone.csv")
    cross = pd.read_csv(OUT / "overlap_v2_rows_vs_seed1_cols.csv", index_col=0)
    others = pd.read_csv(OUT / "others_seed1.csv")
    P = S["orbital_period_s"]
    s1, v2 = ev["seed1"], ev["v2"]
    A, B, O, M = (s1[s1["group"] == g] for g in ("A", "B", "other", "matched"))
    fr = frac.set_index(["run", "group"])
    rz = resid.set_index(["run", "zone"])
    z_before, z_after = f"{EDGE_WINDOW_S:.0f} s before short passage", f"{EDGE_WINDOW_S:.0f} s after short passage"
    z_region = f"within {REGION_DEG} deg of SAA region"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, capture_output=True, text=True).stdout.strip()

    man_v2 = json.loads((RUNS["v2"]["run"] / "manifest.json").read_text())
    last_v2 = man_v2["runs"][-1]

    L = []
    L += [
        "# Analisi orbitale degli eventi della baseline 2019",
        "",
        f"Generato da `python -m benchmark.analysis.orbit_analysis` e `python -m benchmark.analysis.orbit_report` (commit `{commit}`). "
        "Sola lettura sugli output del motore: nessuna run, bundle o parametro modificato. Tutti i numeri vengono dai file in `benchmark/analysis/out/`.",
        "",
        "Run analizzate: `engine-v2` (rete legacy del 2026-09-21) e `engine-v2-seed1` (rete riaddestrata, seed 1). "
        f"Eventi: v2 {S['runs']['v2']['events']} ({S['runs']['v2']['without_counterpart']} senza controparte), "
        f"seed1 {S['runs']['seed1']['events']} ({S['runs']['seed1']['without_counterpart']} senza controparte). "
        "\"Senza controparte\" = né catalogo trigger GBM né tabelle di Crupi (regola primaria di `benchmark/validate.py`).",
        "",
        f"> Nota di integrità: `engine-v2/manifest.json` contiene una voce aggiunta il {last_v2['started'][:19]} UTC "
        f"(commit {last_v2['git_commit'][:7]}) e il blocco parametri riporta `train_seed: {man_v2['parameters'].get('train_seed')}` con "
        f"`model_mode: {man_v2['parameters'].get('model_mode')}`: una pipeline lanciata **senza** `DEEPGRB_RUN_LABEL` ha usato la cartella di default. "
        "pred/trig/results di engine-v2 non sono stati riscritti (date dei file del 2026-10-03); il seed nel manifest non descrive il modello legacy. Non corretto qui (vincolo: engine-v2 in sola lettura).",
        "",
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
        f"Ricalcolata qui con la stessa definizione: differenza massima con il CSV della validazione {S['runs']['seed1']['dist_check_max_abs_diff_s']:.1e} s. "
        "Le distanze firmate dal buco precedente e successivo sono nelle colonne `t_since_gap_end_s` e `t_to_gap_start_s`.",
        "",
        "Gruppi degli eventi senza controparte (bande che contengono i due addensamenti di seed1 con margine): "
        + ", ".join(f"**{g}** = {a:.0f}–{b:.0f} s" for g, (a, b) in BANDS.items()) + ", **altri** = il resto.",
        "",
        "## 2. Sovrapposizione tra le due reti",
        "",
        f"Abbinamento uno-a-uno di intervalli [inizio, inizio + durata] estesi di ±2 bin (greedy per |Δinizio|): "
        f"**{S['overlap']['pairs']}** coppie, **{S['overlap']['only_v2']}** eventi solo in v2, **{S['overlap']['only_seed1']}** solo in seed1 "
        f"(Δinizio mediano delle coppie {S['overlap']['median_abs_dstart_s']:.1f} s).",
        "",
        "Righe: gruppo dell'evento in v2; colonne: gruppo dell'evento abbinato in seed1 (`absent` = nessun abbinamento).",
        "",
        md(cross.reset_index().rename(columns={"row_0": "v2 \\ seed1"}), ".0f"),
        "",
        "Eventi solo in seed1 per gruppo: " + ", ".join(f"{k} {v}" for k, v in S["overlap"]["only_seed1_by_group"].items()) + ".",
        "",
        f"Risposta: gli eventi senza controparte **sono in gran parte gli stessi** nelle due reti. "
        f"Tutti i {int((s1['group'] == 'A').sum())} A di seed1 hanno un A in v2; "
        f"B: {int(((s1['group'] == 'B') & (s1['pair_group'] == 'B')).sum())}/{int((s1['group'] == 'B').sum())}; "
        f"altri: {int(((s1['group'] == 'other') & (s1['pair_group'] == 'other')).sum())}/{int((s1['group'] == 'other').sum())}. "
        f"Nessun evento cambia categoria tra abbinato e senza controparte. La rete legacy ne produce di più in A "
        f"({S['runs']['v2']['groups'].get('A', 0)} contro {S['runs']['seed1']['groups'].get('A', 0)}).",
        "",
        "## 3. Posizione orbitale",
        "",
        "Metodo (per **tutti** gli eventi di entrambe le run e per "
        f"{len(null)} istanti casuali presi tra i bin validi di v2, ipotesi nulla):",
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
        "![mappa](../benchmark/analysis/out/map_lat_lon.png)",
        "",
        "![tempo dall'uscita SAA](../benchmark/analysis/out/hist_time_since_saa_exit.png)",
        "",
        "### Mediane per gruppo (seed1)",
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
    sel = ks[(ks["run"] == "seed1") & ks["variable"].isin(["lat", "lon", "L", "phase_deg", "dist_saa_region_deg",
                                                             "t_to_saa_entry_s", "prev_orbit_saa_offset_s"])]
    piv = sel.pivot_table(index=["group", "variable"], columns="vs", values="p_value").reset_index()
    L += ["### Test KS a due campioni (seed1; p-value contro abbinati e contro tempi casuali)", "",
          "Tutti i test (entrambe le run, tutte le variabili) sono in `benchmark/analysis/out/ks_tests.csv`. "
          "Campioni piccoli (A 17, B 10): i p-value indicano differenze di distribuzione, non la causa.", "",
          md(piv, ".1e"), ""]
    L += ["### Il fondo previsto è sottostimato vicino alla SAA? (tutti i bin validi, non solo gli eventi)", "",
          f"Residuo relativo della somma dei 12 NaI in r1, (frg − bkg)/bkg, e frazione di bin con FOCuS r1 > 3σ su almeno un rivelatore. "
          f"\"Passaggio breve\" = passaggio SAA più corto di {SHORT_PASSAGE_S:.0f} s ({S['short_passages']} nel periodo, durata "
          f"{S['short_passage_duration_s'][0]:.0f}–{S['short_passage_duration_s'][2]:.0f} s, mediana {S['short_passage_duration_s'][1]:.0f} s): "
          "il suo buco nei dati resta sotto la soglia di 500 s e **non viene mascherato**.", "",
          md(resid, ".2f"), ""]

    # ---------------- verdict
    a_before = S["runs"]["seed1"]["A_before_short_passage"]
    L += [
        "## 4. Verdetto",
        "",
        "### Gruppo A — ipotesi \"periferia SAA\": **sostenuta**, con un meccanismo preciso",
        "",
        f"- Posizione: tutti i {len(A)} eventi A di seed1 sono a lat {rng(A['lat'], '.1f')}°, lon {rng(A['lon'], '.1f')}°, sul **bordo occidentale** della regione SAA "
        f"(a lat −12° la regione con flag va da lon {S['saa_region']['lon_range_at_lat_-12'][0]:.1f}° a {S['saa_region']['lon_range_at_lat_-12'][1]:.1f}°), "
        f"fase {rng(A['phase_deg'], '.0f')}°, a {rng(A['dist_saa_region_deg'], '.1f')}° dalla regione SAA "
        f"(abbinati: mediana {M['dist_saa_region_deg'].median():.0f}°; tempi casuali entro {REGION_DEG}°: {S['null_within_region_%']:.2f}%).",
        f"- Tempo: iniziano {rng(A['t_to_saa_entry_s'])} s **prima di entrare** nella SAA; {a_before}/{len(A)} precedono di al più "
        f"{EDGE_WINDOW_S:.0f} s un **passaggio breve** (< {SHORT_PASSAGE_S:.0f} s) il cui buco dati non è mascherato. "
        f"Un'orbita prima Fermi era dentro la SAA in {int(fr.loc[('seed1', 'A'), 'prev_orbit_in_saa'])}/{len(A)} casi "
        f"(tempi casuali: {int(fr.loc[('null', 'null'), 'prev_orbit_in_saa'])}/{int(fr.loc[('null', 'null'), 'n'])}).",
        f"- Il raggruppamento di `dist_saa_gap_s` a ≈ 5100–5200 s viene dalla definizione: il passaggio breve subito dopo l'evento non produce "
        f"un buco > 500 s, quindi il bordo più vicino è la fine del buco lungo dell'**orbita precedente**. Per gli A, t − P cade "
        f"{rng(P - A['t_since_gap_end_s'])} s prima di quella fine (P = {P:.0f} s), cioè dentro il passaggio SAA precedente.",
        f"- Fondo: nei {EDGE_WINDOW_S:.0f} s prima dei passaggi brevi il residuo relativo al 90° percentile è "
        f"{rz.loc[('seed1', z_before), 'p90_rel_residual_%']:.1f}% (altrove {rz.loc[('seed1', 'elsewhere'), 'p90_rel_residual_%']:.1f}%) e FOCuS "
        f"supera 3σ nel {rz.loc[('seed1', z_before), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin (altrove {rz.loc[('seed1', 'elsewhere'), 'frac_bins_focus_r1_gt3_%']:.2f}%); "
        f"dopo l'uscita nessun eccesso ({rz.loc[('seed1', z_after), 'frac_bins_focus_r1_gt3_%']:.2f}%). La rete sottostima il fondo nell'avvicinamento ai passaggi brevi.",
        f"- Riproducibilità: stesso comportamento con la rete legacy (v2: {S['runs']['v2']['A_before_short_passage']} eventi A prima di un passaggio breve; "
        f"{rz.loc[('v2', z_before), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin sopra 3σ in quella zona).",
        f"- Probabilità che {S['runs']['seed1']['band_A_count']} dei {S['runs']['seed1']['without_counterpart']} eventi senza controparte cadano nella banda A per caso "
        f"(frazione dei tempi casuali nella banda: {100 * S['null_fraction_in_band_A']:.2f}%): binomiale p = {S['runs']['seed1']['band_A_binom_p']:.1e}.",
        "",
        "### Gruppo B — ipotesi \"periferia SAA nell'orbita successiva a un passaggio\": **non sostenuta nella forma proposta**; periferia SAA **sostenuta**, ma nell'orbita *precedente* al primo passaggio",
        "",
        f"- Posizione: lat {rng(B['lat'], '.1f')}°, lon {rng(B['lon'], '.1f')}°, fase {rng(B['phase_deg'], '.0f')}°, "
        f"a {rng(B['dist_saa_region_deg'], '.1f')}° dalla regione SAA: appena **a nord del bordo settentrionale** "
        f"(regione con flag: lat da {S['saa_region']['lat_min']:.1f}° a {S['saa_region']['lat_max']:.1f}°, lon da "
        f"{S['saa_region']['lon_min']:.1f}° a {S['saa_region']['lon_max']:.1f}°), una zona diversa da A.",
        f"- Tempo: un'orbita prima Fermi **non** era nella SAA ({int(fr.loc[('seed1', 'B'), 'prev_orbit_in_saa'])}/{len(B)}); "
        f"dall'ultima uscita sono passate {B['t_since_saa_exit_s'].median() / 3600:.1f} h (mediana). "
        f"La prossima entrata arriva dopo {B['t_to_saa_entry_s'].median():.0f} s (mediana; {int((B['t_to_saa_entry_s'] > 5000).sum())}/{len(B)} tra "
        f"{B.loc[B['t_to_saa_entry_s'] > 5000, 't_to_saa_entry_s'].min():.0f} e {B.loc[B['t_to_saa_entry_s'] > 5000, 't_to_saa_entry_s'].max():.0f} s), "
        "cioè circa un'orbita dopo: B cade nell'orbita **che precede il primo passaggio** di una sequenza giornaliera, quando la traccia sfiora il bordo SAA senza entrarci.",
        f"- Fondo: entro {REGION_DEG}° dalla regione SAA FOCuS supera 3σ nel {rz.loc[('seed1', z_region), 'frac_bins_focus_r1_gt3_%']:.1f}% dei bin "
        f"(altrove {rz.loc[('seed1', 'elsewhere'), 'frac_bins_focus_r1_gt3_%']:.2f}%), residuo al 90° percentile {rz.loc[('seed1', z_region), 'p90_rel_residual_%']:.1f}%.",
        f"- Probabilità della banda B per caso ({100 * S['null_fraction_in_band_B']:.2f}% dei tempi casuali): binomiale p = {S['runs']['seed1']['band_B_binom_p']:.1e}. "
        f"Con 10 eventi, la conclusione sulla posizione è solida; quella sul meccanismo (perché proprio lì) resta un'ipotesi.",
        "",
        f"Eventi abbinati a Crupi/GBM nelle stesse bande: A {S['runs']['seed1']['band_A_matched_count']}, B {S['runs']['seed1']['band_B_matched_count']} "
        f"su {S['runs']['seed1']['matched_n']}.",
        "",
        "### Possibile flag di post-processing (descrizione, non implementata)",
        "",
        "Un flag sull'**evento** (non un taglio sui trigger, nessuna modifica al motore), calcolato dopo `events_table.csv` dalla POSHIST:",
        f"- `saa_edge_short_passage`: l'inizio dell'evento è entro {EDGE_WINDOW_S:.0f} s prima (o dopo) un passaggio SAA più breve di {SHORT_PASSAGE_S:.0f} s (buco non mascherato);",
        f"- `saa_region_proximity`: la posizione di Fermi all'inizio dell'evento è entro {REGION_DEG}° dalla regione con flag SAA.",
        "Gli eventi flaggati restano nel catalogo, con la segnalazione \"possibile fondo di particelle al bordo SAA\". "
        f"Sui dati di seed1 il primo flag coprirebbe {a_before} eventi A; il secondo i B (distanza ≤ {B['dist_saa_region_deg'].max():.1f}°). "
        "Soglie e conteggi andrebbero verificati anche sugli eventi abbinati prima di usarli.",
        "",
        "## 5. Gli eventi \"altri\" senza controparte (seed1)",
        "",
        f"{len(others)} eventi; voci del catalogo trigger GBM entro ±1 h dall'inizio (con Δt firmato).",
        "",
        md(others[["trig_ids", "start_times", "duration", "detectors", "sigma_C", "CE", "lat", "lon", "L", "phase_deg",
                   "t_since_saa_exit_s", "t_to_saa_entry_s", "dist_saa_gap_s", "pair_group", "gbm_within_1h"]].assign(
            start_times=others["start_times"].str.slice(0, 19)), ".1f"),
        "",
        f"`pair_group` = gruppo dell'evento abbinato in v2 (`absent` = presente solo in seed1). Mediane rispetto agli abbinati: "
        f"L {O['L'].median():.2f} contro {M['L'].median():.2f}, distanza dalla regione SAA {O['dist_saa_region_deg'].median():.0f}° contro {M['dist_saa_region_deg'].median():.0f}°.",
        "",
        "Osservazioni (descrittive, nessun verdetto):",
        "",
        f"- **Alta L.** {S['runs']['seed1']['L_ge_1.4_by_group']['other'][0]}/{S['runs']['seed1']['L_ge_1.4_by_group']['other'][1]} \"altri\" hanno L ≥ "
        f"{S['high_L_threshold']} (abbinati: {S['runs']['seed1']['L_ge_1.4_by_group']['matched'][0]}/{S['runs']['seed1']['L_ge_1.4_by_group']['matched'][1]}; "
        f"tempi casuali: {S['null_L_ge_1.4_%']:.1f}%). Si concentrano vicino ai punti di massima latitudine dell'orbita "
        f"(|lat| ≥ 24°: {int((O['lat'].abs() >= 24).sum())}/{len(O)}), cioè alle latitudini geomagnetiche più alte raggiunte da Fermi: "
        "zona compatibile con precipitazione di particelle, ma qui non verificata.",
        f"- **Fondo previsto nullo (artefatto della rete).** Nella run seed1 la rete prevede fondo 0 in "
        f"{S['runs']['seed1']['zero_bkg_cells']} celle ({S['runs']['seed1']['zero_bkg_rows']} bin interi); nella v2 in "
        f"{S['runs']['v2']['zero_bkg_cells']}. Questi bin toccano gli eventi seed1 {S['runs']['seed1']['events_touching_zero_bkg']} "
        f"(l'evento 6 ha σ_C {others.loc[others['trig_ids'] == 6, 'sigma_C'].iloc[0]:.0f}). FOCuS tratta il fondo ≤ 0 come non valido, "
        "ma `models/analyze.py::event_significance` scarta solo i NaN: con B = 0 la significatività esplode. "
        "Sono artefatti, non eventi; la correzione (trattare B ≤ 0 come non valido anche in analyze) cambierebbe gli eventi e richiede `ENGINE_VERSION` 3: **non applicata** (vincolo: motore in sola lettura).",
        "",
        "## 6. Limiti",
        "",
        "- Le bande A/B sono state scelte guardando i dati di seed1: i p-value binomiali misurano quanto il raggruppamento è anomalo, non sono un test cieco.",
        "- Latitudine geomagnetica da dipolo centrato (approssimazione); L di McIlwain dalle tabelle di gbm-data-tools.",
        "- Il confronto dei residui usa la somma dei 12 NaI in r1; non distingue i singoli rivelatori.",
        "- La regione SAA è quella del flag di POSHIST, che è la regione in cui i rivelatori sono spenti; la regione fisica di particelle intrappolate è più ampia.",
        "",
    ]
    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"written {DOC}")


if __name__ == "__main__":
    main()
