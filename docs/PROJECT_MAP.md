# DeepGRB — mappa del progetto (stato al 2026-10-04)

Documento autosufficiente per chi non ha accesso al repository: struttura, ruolo e stato di ogni file, flusso dei dati, convenzioni e vincoli, e un elenco di **disomogeneità** attuali (fatti, non ancora decisioni) da cui partire per rendere il progetto più uniforme.

- Repository: fork di `github.com/rcrupi/DeepGRB` (Crupi et al. 2023), branch di lavoro `fix/baseline-2019` (46 commit sopra `thesis`, solo locali).
- Ambiente: conda `deepgrb_recas`, Python 3.9.23, TensorFlow 2.20 / Keras 3.10, pandas 1.5.3, numpy 1.26.4, gbm-data-tools 1.1.1. Cluster ReCaS (GPU solo su alcuni nodi).
- Scopo scientifico: cercare transienti gamma nei dati Fermi/GBM. Una rete neurale stima il fondo, Poisson-FOCuS cerca gli eccessi, gli eventi vengono localizzati, classificati con regole euristiche e validati contro il catalogo GBM e le tabelle del paper di Crupi.
- Stato: baseline 2019 validata (periodo 2019-03-01 → 2019-06-30). Risultati in `docs/BASELINE_2019.md`, storia completa in `docs/WORKLOG.md`.

---

## 1. Albero

Legenda stato: **A** = attivo e testato; **T** = strumento di analisi/validazione attivo; **L** = legacy (non usato dalla pipeline, spesso con percorsi vecchi); **O** = obsoleto/archiviato; **D** = dati o output.

```
DeepGRB/
├── docs/WORKING_RULES.md                     A  regole operative e piano a fasi (documento guida del lavoro)
├── README.md, readme.txt         L  README originale di Crupi: descrive la pipeline vecchia (Python 3.6.8, percorsi vecchi)
├── requirements.txt              A  dipendenze pinnate (manca tabulate; tsfel e xgboost non installati)
├── LICENSE, .gitignore
├── fetch_fermi_triggers.py       L  scarica trigger GBM per la vecchia sandbox di gennaio 2019
├── report.log                    O  log della vecchia pipeline (numeri invalidi)
├── seed1_files.tar.gz            D  archivio creato dall'utente (non toccato)
│
├── connections/                  accesso a Fermi e configurazione
│   ├── __init__.py               A  re-export di fermi_data_tools
│   ├── fermi_data_tools.py       A  catalogo trigger GBM (HEASARC) e burst catalog → data/gbm_trig_catalog.csv, gbm_burst_catalog.db
│   └── utils/config.py           A  CONFIG CENTRALE: date, cartelle, ENGINE_VERSION, run_dir()
│       └── m_check/saved_model.keras  O  modello legacy di upstream, non referenziato
│
├── utils/                        utilità generiche
│   ├── keys.py                   A  nomi dei 36 canali NaI (n0_r0 … nb_r2)
│   ├── period.py                 A  finestre di date inclusive
│   ├── fermi_time.py             A  conversione UTC ↔ MET (solo astropy)
│   ├── run_options.py            A  variabili d'ambiente → cartella di run, bundle, modalità del modello
│   └── config.py                 O  vuoto
│
├── models/                       MOTORE (step 1-5 della pipeline + localizzazione/classificazione/flag)
│   ├── __init__.py               A  re-export (EventAnalyzer, download_spec, CrupiEventClassifier, df_burst_catalog)
│   ├── download_bkg.py           A  step 1: download CSPEC/POSHIST idempotente, per file, con verifica FITS
│   ├── preprocess.py             A  step 2: tabelle giornaliere data/bkg/YYMMDD.csv (rate 4.096 s + feature orbitali)
│   ├── model_nn.py               A  step 3: rete 60→2048→2048→1024→36; bundle (modello+scaler+metadata); predict → pred/
│   ├── trigger.py                A  step 4: Poisson-FOCuS sui 36 canali → trig/
│   ├── trigs/focus.py            A  implementazione Poisson-FOCuS (identica a upstream)
│   ├── trigs/paramtrig.py        L  trigger "stile GBM di bordo", non usato
│   ├── analyze.py                A  step 5: trigger → eventi, significatività S per evento, C, tier CE → results/
│   ├── localize_event.py         A  localizzazione PSO + Monte Carlo (usata da benchmark/classify)
│   ├── loc/localization_class.py A  classe Localization (PSO); commenti in italiano
│   ├── event_classifier.py       A  regole euristiche di Crupi (GRB, SF, TGF, GF, UNC(LP), UNC), senza leakage
│   ├── saa_flags.py              A  flag di post-processing: saa_edge_short_passage, saa_region_proximity, near_zero_prediction
│   ├── load_data.py              L  burst catalog per script di analisi (usato solo da scripts/VAE_gen_redshift/regressionT90.py)
│   └── utils/
│       ├── config.py             L  lista di colonne spettrali del burst catalog (per load_data)
│       ├── losses.py             A  loss custom (median/max); commenti in italiano
│       └── GBMutils.py           L  add_trig_gbm_to_frg (riscrive frg: non più chiamato), update_gbm_db
│
├── pipeline/
│   ├── pipeline_bkg.py           A  ENTRY POINT: step 1-5 per un periodo, cartella di run versionata, manifest
│   ├── manual_label.py           L  etichette posizionali di Crupi (2010-11, 2014, 2019)
│   ├── script_to_latex.py        L  tabelle LaTeX del paper (percorsi e etichette vecchi)
│   ├── train_classifier.py       L  esperimento RF/DT di Crupi (percorsi vecchi)
│   └── run_classification.txt    L  output storico di Crupi
│
├── benchmark/                    VALIDAZIONE, ANALISI E STRUMENTI (non modificano il motore)
│   ├── validate.py               T  validazione deterministica (catalogo GBM + tabelle Crupi) → benchmark/out/<run>/REPORT.md + CSV
│   ├── matching.py               T  abbinamento uno-a-uno (riferimento→evento; evento↔evento)
│   ├── classify.py               T  localizza + classifica una run → results/events_table_loc.csv, events_classified.csv
│   ├── baseline_doc.py           T  genera docs/BASELINE_2019.md (numeri e checksum dai file)
│   ├── reference/                D  crupi_2019_known.csv (74), crupi_2019_unknown.csv (25): verità del paper
│   ├── audit/
│   │   ├── data_inventory.py     T  copertura dati giorno per giorno → docs/DATA_INVENTORY.md
│   │   ├── engine_checks.py      T  controlli di accettazione del motore (fondo, SAA, S ricalcolata)
│   │   ├── compare_runs.py       T  confronto eventi tra due run (prima/dopo)
│   │   └── sensitivity_tmax.py   T  sensibilità a dmax=120.4 s (run separata)
│   ├── analysis/
│   │   ├── orbit_analysis.py     T  posizione orbitale degli eventi, gruppi A/B, nulla casuale, KS
│   │   ├── orbit_report.py       T  genera docs/ORBIT_ANALYSIS.md
│   │   ├── zero_prediction.py    T  diagnosi dei bin con fondo previsto 0 (rete seed1)
│   │   ├── lr_check.py           T  MAE di predittori banali (riferimento per la convergenza)
│   │   └── out/                  D  output delle analisi (non versionato)
│   ├── out/                      D  report di validazione: radice = engine-v2, seed1/, v3/, v3-seed1/, sensitivity_tmax29/
│   └── _obsolete/                O  vecchio report scritto a mano (INVALIDO), validate_results.py, test_pipeline_sandbox.py
│
├── scripts/                      L  analisi esplorative di Crupi (plot, posizionamento, VAE/redshift)
│   ├── bkg/ …                    L  usano i percorsi vecchi data/pred/frg_<mesi>.csv
│   └── VAE_gen_redshift/ …       L  esperimenti separati (autoencoder, regressione T90); non è un VAE né riguarda il redshift
│
├── tests/                        A  88 test unittest sulle funzioni reali (python -m unittest discover -s tests -t .)
│
├── docs/
│   ├── BASELINE_2019.md          documento di riferimento della baseline (generato)
│   ├── BASELINE.md               guida pratica: comandi, cache, periodi
│   ├── WORKLOG.md                diario di tutte le modifiche, con numeri misurati
│   ├── DIFF_UPSTREAM.md          differenze fork ↔ upstream (fase 0)
│   ├── ORBIT_ANALYSIS.md         analisi orbitale degli eventi senza controparte (generato)
│   ├── DATA_INVENTORY.md, data_inventory.csv   copertura dati (generato)
│   └── PROJECT_MAP.md            questo documento
│
├── data/                         D  (quasi tutto non versionato)
│   ├── cspec/, poshist/          file grezzi Fermi (≈18 GB + 2 GB)
│   ├── bkg/                      122 tabelle giornaliere YYMMDD.csv (≈6 GB)
│   ├── runs/<start>_<end>/engine-v<N>[-<etichetta>]/   OUTPUT DEL MOTORE (vedi §3)
│   ├── nn_model/                 bundles/<nome>/ (modello + scaler + metadata) e il .h5 legacy di partenza
│   ├── gbm_trig_catalog.csv, gbm_burst_catalog.db, DeepGRB_catalog.csv   cataloghi
│   ├── pred/, trig/, results/    L  output della VECCHIA pipeline (pred/trig già sovrascritti: invalidi)
│   ├── grb_classification/, plots/   vuote
│   └── _archive_20261003/        stati congelati e invalidati (mai cancellati)
├── data_test/                    L  sandbox di una settimana di gennaio 2019 (vecchia, 2.5 GB)
└── logs/                         log delle esecuzioni (non versionato)
```

---

## 2. Come funziona la pipeline

Comando: `python -u pipeline/pipeline_bkg.py` (dalla radice). Il periodo e le opzioni si scelgono con variabili d'ambiente (§4).

| Step | Modulo | Input | Output | Note |
|---|---|---|---|---|
| 1 download | `models/download_bkg.py` | HEASARC FTP | `data/cspec/`, `data/poshist/` | idempotente; saltabile con `DEEPGRB_SKIP_DOWNLOAD=1` |
| 2 preprocess | `models/preprocess.py` | CSPEC+POSHIST | `data/bkg/YYMMDD.csv` | solo giorni mancanti; 36 rate NaI (3 bande) + feature orbitali, bin 4.096 s |
| 3 fondo | `models/model_nn.py` | `data/bkg/*.csv`, bundle | `run/pred/frg.csv`, `bkg.csv` | maschera ±150 bin attorno ai buchi > 500 s; zero-count → NaN; UTC |
| 4 FOCuS | `models/trigger.py`, `trigs/focus.py` | pred | `run/trig/trig.csv`, `offset.csv` | mu_min 1.2, t_max 50 bin; celle non valide → NaN (reset) |
| 5 eventi | `models/analyze.py` | pred + trig + catalogo | `run/results/triggers_table.csv`, `events_table.csv` | soglia 3σ in r1, merge 600 s, S con taglio sui quantili, C, CE; da v3 B ≤ 0 ignorato |

Fuori dalla pipeline, da lanciare dopo:

| Strumento | Cosa fa | Output |
|---|---|---|
| `python -m benchmark.classify --run <run> --jobs 4` | localizzazione PSO + regole euristiche | `run/results/events_table_loc.csv`, `events_classified.csv` |
| `python -m benchmark.validate --run <run> --out <dir>` | validazione + flag di post-processing | `<dir>/REPORT.md`, `matches_*.csv`, `events_flags.csv`, … |
| `python -m benchmark.audit.engine_checks` | controlli del motore | `run/results/engine_checks.md` |
| `python -m benchmark.baseline_doc` | documento di riferimento | `docs/BASELINE_2019.md` |

Le scelte scientifiche (rate a FOCuS, ±150 bin, t_max 50 bin) seguono il codice di upstream e sono documentate in `docs/WORKING_RULES.md` §2.

---

## 3. Cartelle di run, bundle e manifest

- `data/runs/<start>_<end>/engine-v<ENGINE_VERSION>[-<etichetta>]/`: `manifest.json`, `pred/`, `trig/`, `results/`. Una run senza etichetta usa la cartella come cache (gli step con output presenti vengono saltati); una run etichettata non deve esistere e non viene mai sovrascritta.
- `ENGINE_VERSION = 3` (`connections/utils/config.py`). v3 = v2 con S che ignora B ≤ 0. Le run v3 riusano `pred/` e `trig/` della v2 corrispondente tramite **symlink** (dichiarato in `manifest.json → reused_from`).
- Run esistenti per il 2019: `engine-v2` (rete legacy), `engine-v2-seed1` (rete riaddestrata, seed 1), `engine-v2-sens-tmax29` (sensibilità), `engine-v3` (legacy, riuso), `engine-v3-seed1` (**riferimento**, riuso).
- Bundle in `data/nn_model/bundles/<nome>/`: `model.keras|.h5`, `scaler.joblib`, `metadata.json` (seed, periodo, versioni, MAE per canale, durata, commit, convergenza).
- `manifest.json`: parametri, storia delle esecuzioni (commit, versioni), `reused_from`, `predicted_zero_cells`.

---

## 4. Variabili d'ambiente

| Variabile | Effetto |
|---|---|
| `DEEPGRB_START_DATE`, `DEEPGRB_END_DATE` | periodo (default 2019-03-01, 2019-06-30) |
| `DEEPGRB_RUN_LABEL` | run e bundle separati `…-<etichetta>` |
| `DEEPGRB_FORCE_TRAIN=1` | addestra una nuova rete (richiede etichetta e seed; mai il modello legacy) |
| `DEEPGRB_TRAIN_SEED` | seed di python/numpy/TensorFlow |
| `DEEPGRB_REUSE_BUNDLE=1` | usa un bundle etichettato esistente |
| `DEEPGRB_ALLOW_TRAINING=1` | consente il training per periodi senza bundle |
| `DEEPGRB_SKIP_DOWNLOAD=1` | salta gli step 1-2 (verifica solo le tabelle giornaliere) |

---

## 5. Convenzioni attuali e vincoli

- Codice, commit e nomi in inglese; documenti e dialogo in italiano.
- Nessun numero scritto a mano nei report: generati da script che leggono file (`validate.py`, `orbit_report.py`, `baseline_doc.py`).
- Mai sovrascrivere input (`pred/`, `trig/`, bundle); invalidare spostando in `data/_archive_<data>/`; mai cancellare dati.
- Ogni correzione di bug ha un test sulla funzione reale che fallisce prima e passa dopo; commit piccoli e atomici.
- Non cambiare parametri scientifici per "far tornare i numeri"; un training lungo richiede conferma.
- `docs/WORKING_RULES.md` contiene regole e fasi complete; `docs/WORKLOG.md` la storia.

---

## 6. Disomogeneità attuali (fatti da cui partire)

Elenco osservato sul codice al 2026-10-04; nessuna di queste è stata ancora corretta.

**Struttura e responsabilità**
1. Il motore è in `models/`, ma localizzazione, classificazione e flag non fanno parte della pipeline: si lanciano da `benchmark/` (`classify.py`, `validate.py`). I flag sono calcolati dentro la validazione, non come step del motore.
2. `benchmark/` mescola validazione (`validate.py`, `matching.py`), strumenti di produzione (`classify.py`), generatori di documenti (`baseline_doc.py`, `analysis/orbit_report.py`), audit e analisi.
3. `models/saa_flags.py` contiene anche `near_zero_prediction`, che non riguarda la SAA.
4. `benchmark/validate.py` (630 righe) unisce calcolo, flag e scrittura del report; `md_table` è duplicata in `benchmark/analysis/orbit_report.py` (helper `md`).
5. Funzioni di supporto sparse: conversioni di tempo in `utils/fermi_time.py` e in `models/model_nn.met_to_utc`; abbinamento intervalli in `benchmark/matching.py` ma usato anche dall'analisi.

**Codice legacy ancora presente**
6. Moduli non usati dalla pipeline: `models/trigs/paramtrig.py`, `models/utils/GBMutils.py` (contiene una funzione che riscrive `frg`), `models/load_data.py` + `models/utils/config.py` (solo per uno script), `utils/config.py` (vuoto), `connections/utils/m_check/saved_model.keras`.
7. Nove file usano ancora i percorsi della pipeline vecchia (`data/pred/frg_<mesi>.csv`, `FOLD_RES`, `PATH_TO_SAVE`) e oggi non funzionano con le cartelle di run: `scripts/bkg/*` (5 file), `pipeline/script_to_latex.py`, `pipeline/train_classifier.py`, `models/utils/GBMutils.py`, oltre alle costanti legacy in `connections/utils/config.py`.
8. `pipeline/` contiene sia l'entry point attivo sia tre script legacy di Crupi; `scripts/` è interamente legacy.
9. Dati legacy in `data/pred/`, `data/trig/`, `data/results/` (output invalidi della pipeline vecchia, ≈6 GB) e `data_test/` (sandbox vecchia, 2.5 GB); `report.log`, `fetch_fermi_triggers.py`, `readme.txt` alla radice.
10. `README.md` descrive ancora la pipeline originale (Python 3.6.8, `PATH_TO_SAVE`, comando senza variabili).

**Stile**
11. `logging.basicConfig` chiamato in 25 file (ogni modulo configura il logging globale); formati diversi. Il report di training usa `print(flush=True)`, il resto `logging`.
12. Commenti e docstring in italiano in `utils/keys.py`, `models/utils/losses.py`, `models/loc/localization_class.py`; altrove in inglese.
13. Percorsi: alcuni moduli usano `Path` e parametri espliciti (motore nuovo), altri stringhe concatenate e costanti globali (legacy).
14. Nomi degli output di validazione non uniformi: `benchmark/out/` (radice = engine-v2), `seed1/`, `v3/`, `v3-seed1/`, `sensitivity_tmax29/`; nomi delle run `engine-v2-sens-tmax29` vs `engine-v3-seed1`.
15. Le CLI non hanno tutte la stessa interfaccia: alcune accettano `--run`, altre leggono le run da costanti (`orbit_analysis.py` ha `engine-v2` e `engine-v2-seed1` fissi), altre i nomi da `config`.

**Configurazione e metadati**
16. Configurazione divisa tra `connections/utils/config.py` (date, cartelle, versione), costanti in `pipeline/pipeline_bkg.py` (parametri scientifici), `utils/run_options.py` (variabili d'ambiente, nome del .h5 legacy) e soglie nei singoli moduli (`analyze.py`, `saa_flags.py`, `model_nn.py`).
17. Il manifest di una run riscrive il blocco `parameters` a ogni esecuzione nella stessa cartella: una pipeline lanciata il 2026-10-04 senza etichetta ha lasciato in `engine-v2/manifest.json` un `train_seed: 1` che non descrive il modello legacy.
18. Il bundle della rete seed1 e le cartelle `engine-v2-seed1`, `engine-v3*` non sono versionati; le v3 dipendono dalle v2 tramite symlink.

**Dipendenze**
19. `requirements.txt` non include `tabulate` (assente: pandas `to_markdown` non funziona), né `tsfel` e `xgboost`, che serviranno per la fase XGBoost.

---

## 7. Lavori aperti noti (da docs/WORKING_RULES.md e WORKLOG)

- Fase 6 (XGBoost): portare le feature `fe_*` (tsfel, branch upstream `ric_review_28062023`), eseguire il motore su 2010-11 e 2014 per avere i 324 eventi etichettati di Crupi.
- Localizzazione: eseguita e deterministica ma non validata contro le posizioni dei cataloghi.
- Rivelatore nb sovrarappresentato negli eventi senza controparte: causa non determinata.
- Stabilità rispetto alla rete: due addestramenti (144 vs 136 eventi); test con più seed solo su richiesta.
