# Consolidamento del framework DeepGRB — resoconto

Consolidamento eseguito il 2026-10-04 sul branch `fix/baseline-2019`, da `e0e8da3` (tag `baseline-2019-validated` = `e4675cc`, più due commit di documentazione) a `2465c0d`. È un refactoring: la scienza non cambia. I numeri di questo documento vengono da file o da comandi (sezione 10).

## 1. Obiettivo e stato di partenza

**Obiettivo** (prompt di consolidamento, §0): un `main` con il minimo indispensabile di file, fedele alla struttura di Crupi (`connections/`, `utils/`, `models/`, `pipeline/`, `data/`), senza l'impalcatura di lavoro; una pipeline semplice e un resoconto scientifico leggibile per ogni run; crediti a Crupi e agli altri autori.

**Stato di partenza** (`e0e8da3`, descritto in `docs/PROJECT_MAP.md`, ora nella storia git):

- 161 file tracciati (315.3 MB), di cui 75 Python, 7645 righe senza i test;
- un entry point per gli step 1–5, mentre localizzazione, classificazione, flag e validazione si lanciavano a parte da `benchmark/`;
- 25 chiamate a `logging.basicConfig`, configurazione sparsa in quattro posti, codice legacy non funzionante;
- tre file > 70 MB nel repo (`.h5` legacy, `m_check/saved_model.keras`, due modelli in `data_test/`).

Le 19 disomogeneità censite sono riprese nella tabella della sezione 3.

**Congelamento** (§1 del prompt):

- `git status` pulito;
- il tag `baseline-2019-validated` esisteva già ed era già sul remote: non è stato ricreato;
- `git bundle create ../deepgrb_pre_consolidation.bundle --all` (738 MB, fuori dal repo);
- invarianti registrati prima di ogni modifica (sezione 2, commit `e0e8da3`).

**Stato finale** (`2465c0d`):

- 103 file tracciati (5.0 MB), di cui 54 Python, 6190 righe senza i test;
- 104 test verdi (erano 88);
- nessun file tracciato oltre 5 MB.

## 2. Invarianti e prova

### 2.1 Checksum da riprodurre (registrati prima del refactoring)

| file | sha256 |
|---|---|
| `engine-v3-seed1/results/events_table.csv` | `eb0207fb7b96acef9c677b250a3f0f00503dacb18bf8d76e6d25db7cc02ed051` |
| `engine-v3-seed1/results/events_classified.csv` | `7924b0d67c200b9e15f40a100b8c153dd84d49fe500fb4113ecf968d692b86d0` |
| `engine-v3-seed1/results/triggers_table.csv` | `b430d5e70dc4be9fb83e79a335cc54f2beb6861ec0aa79810c73108523ffc474` |
| `engine-v3-seed1/results/events_table_loc.csv` | `0346fec93a02e9981acc9c1ce6e84031590b5665ae95ac645dfc1b1cc13fd418` |
| `engine-v3/results/events_table.csv` | `78f547180badac51e47061c6513bb5ed42a9e0b4f3763fb20671b7313dc32ae6` |
| `engine-v3/results/triggers_table.csv` | `e9bab9e930fc15f393be9e7dfcb51bb2f93aae8c3c15b081d582e20c520965cb` |

Controllo aggiuntivo sul calcolo della validazione, da `benchmark/out/<run>/`:

| run | file | sha256 |
|---|---|---|
| v3-seed1 | matches_crupi_known.csv | `5f4c1891d40a58751b319df6001ee1109662966da04d7973bec7197da2176721` |
| v3-seed1 | matches_crupi_unknown.csv | `064710cf8beaef59a232ecb082a99468b201a14d63f81cf249198b29fa69d5e4` |
| v3-seed1 | matches_gbm_catalog.csv | `7677e5030eb663164453ddc7a0c547a58166d2905bf0bfe2a073fd184ba77c99` |
| v3-seed1 | events_flags.csv | `d83f587c271a8e893f6d388efd41898d83ba030cc3b7a78cc08fe44f2a6c517d` |
| v3 | matches_crupi_known.csv | `bc3cbc90d3b415dd84da726d9db9cd657dd0c51b2ed64988d743dc361d3688cd` |
| v3 | matches_crupi_unknown.csv | `01cc5a6d2115cbcadb457f606a88df135d5ce3ae1d73e668632cdb028974ae1c` |
| v3 | matches_gbm_catalog.csv | `e45ef7f968b086898d085fbe463b7d2595f51b78d46d1a079664d2b0e67d1f79` |
| v3 | events_flags.csv | `0016aff68c243d8a714eefa1db8f7ba4c6c2d508112dedca1cfc9bd6b6356d12` |

### 2.2 Numeri chiave da riprodurre

| run | eventi (R/S/P) | Crupi noti | Crupi inediti | inediti R+S | GBM rivelati/disponibili | GRB | T90 > 4.096 / ≤ 4.096 | senza controparte |
|---|---|---|---|---|---|---|---|---|
| engine-v3-seed1 (riferimento) | 136 (102/11/23) | 70/71 | 21/24 | 15/16 | 67/120 | 59/78 | 54/65 / 5/13 | 46 |
| engine-v3 (legacy) | 144 (105/18/21) | 70/71 | 21/24 | 15/16 | 68/120 | 60/78 | 54/65 / 6/13 | 53 |

### 2.3 Prova

Le due run v3 sono state spostate in `data/_archive_20261004/` (regola 5 di docs/WORKING_RULES.md: si invalida una cache spostando, mai cancellando). Poi la pipeline consolidata le ha rigenerate con il **codice finale** (commit `544a70d`):

- step 3 come symlink a pred/ e trig/ delle run v2, senza training e senza FOCuS;
- step 4 saltato;
- step 5–9 eseguiti (comandi nella sezione 10).

Esito, con confronto byte per byte (`cmp`):

- `engine-v3-seed1`:
  - `events_table`, `triggers_table`, `events_table_loc` ed `events_classified` hanno **gli stessi sha256** della tabella 2.1;
  - i quattro CSV di validazione sono identici, dove `validation/events_counterparts.csv` corrisponde al vecchio `events_flags.csv`;
  - sono identici anche `sensitivity.csv`, `events_without_counterpart.csv` e `classification_vs_crupi.csv`.
- `engine-v3`:
  - `events_table` e `triggers_table` hanno gli stessi sha256;
  - i CSV di validazione sono identici;
  - `events_without_counterpart.csv` coincide sulle colonne di prima, più quattro colonne di classificazione che prima mancavano: lo step 6 non era mai stato eseguito su questa run, ora fa parte della pipeline;
  - localizzazione e classificazione sono identiche tra due rigenerazioni successive (sha `3b937f0e…` e `ccb16d8b…`).
- Numeri: 136 (102/11/23), 70/71, 21/24, 15/16, 67/120, 59/78, 54/65 e 5/13, 46 senza controparte; legacy 144 (105/18/21), 70/71, 21/24, 68/120, 60/78, 54/65 e 6/13, 53. Coincidono con la tabella 2.2.
- Anche la validazione delle run v2, rifatta con il codice nuovo, produce `matches_*.csv` e `sensitivity.csv` identici a quelli storici di `benchmark/out/`, `benchmark/out/seed1/` e `benchmark/out/sensitivity_tmax29/`.

Una prima rigenerazione era stata fatta sul codice intermedio (`bf188c2`, stesso esito). È conservata in `data/_archive_20261004/intermediate/`.

## 3. Tabella file per file

Difetti numerati come in `docs/PROJECT_MAP.md` (storia git, `e0e8da3`).

| file (prima → dopo) | azione | motivo | difetto | commit |
|---|---|---|---|---|
| `scripts/` (12 file), `pipeline/script_to_latex.py`, `pipeline/run_classification.txt`, `fetch_fermi_triggers.py`, `readme.txt` | rimossi (`git rm`) | legacy con percorsi vecchi, non funzionanti | 7, 8, 9 | `1a204a5` |
| `models/load_data.py`, `models/utils/config.py`, `models/utils/GBMutils.py`, `models/trigs/paramtrig.py`, `utils/config.py` | rimossi | non usati dalla pipeline (GBMutils riscriveva `frg`) | 6, 7 | `1a204a5` |
| `benchmark/_obsolete/` | rimosso | vecchio log INVALIDO e sandbox; restano nella storia e al tag | 2 | `1a204a5` |
| `connections/utils/m_check/`, `data_test/` | non più tracciati, lasciati su disco | modelli legacy da 77 e 2×77 MB | 6, 9 | `1a204a5` |
| `pipeline/manual_label.py`, `pipeline/train_classifier.py` → `docs/legacy_crupi/` | spostati, con README di una riga ciascuno | servono alla fase XGBoost (etichette 2010-11/2014/2019; random forest di Crupi da battere) | 8 | `1a204a5` |
| `models/utils/losses.py` → `models/losses.py` | spostato; commento in inglese | `models/utils/` resta vuota | 12 | `1a204a5` |
| `connections/utils/config.py` | riscritto: configurazione **unica** (cartelle, versione del motore, tutti i parametri scientifici con gli stessi valori, `engine_parameters()`, `run_dir()`, `run_period()`); **nessuna data** | prima: date, costanti legacy e parametri sparsi | 7, 16 | `6cb32c9` |
| `utils/logs.py` | nuovo: logging unico nel formato di Crupi (`%(asctime)s %(levelname)-8s %(message)s`), intestazione, titoli degli step, durate | sostituisce 25 `basicConfig` | 11 | `6cb32c9` |
| `models/*.py`, `connections/fermi_data_tools.py` | logger di modulo; costanti da config; niente date di default | — | 11, 13, 16 | `6cb32c9` |
| `models/saa_flags.py` → `models/flags.py` | rinominato; `flag_events()` = step 7; `event_start_met()` condiviso; CLI `--run` | i flag non sono solo SAA e diventano uno step del motore | 1, 3 | `93065fc`, `7305b3a` |
| `utils/run_options.py` | impostazioni con priorità all'ambiente, ripresa delle run esistenti (`resume`), helper del manifest (modello, checksum del bundle, confronto dei parametri) | sicurezza e difetto 17 | 16, 17 | `3c5f37f` |
| `benchmark/classify.py` → `models.event_classifier.classify_events` | integrato come step 6 (stesse colonne) | — | 1, 2 | `14e5941` |
| `benchmark/analysis/lr_check.py`, `benchmark/audit/sensitivity_tmax.py` | rimossi | analisi una tantum, risultati nel WORKLOG; la run `engine-v2-sens-tmax29` resta | 2 | `1a204a5`, `14e5941` |
| `benchmark/validate.py` (630 righe) | scorporato: solo calcolo → `<run>/validation/` (CSV + `summary.json`) | calcolo e scrittura erano mescolati | 4, 14 | `c1d20a6` |
| `benchmark/report.py` | nuovo: `md_table` unica, `<run>/RESULTS.md`, `docs/RUNS.md` | — | 4 | `c1d20a6`, `f4560e9` |
| `pipeline/pipeline_bkg.py` | riscritto: USER SETTINGS, tabella di stato, 9 step che si saltano da soli, `--jobs`, `--dry-run`, manifest corretto | entry point unico | 1, 16, 17 | `f040d75`, `6c657f9`, `544a70d` |
| `models/loc/localization_class.py` + `pyswarms_logging.yaml` | pyswarms reso innocuo per il logging; docstring in inglese | pyswarms riconfigurava il logging a ogni ottimizzatore e scriveva `./report.log`: era l'origine di quel file | 11, 12 | `ee74676` |
| `utils/keys.py` | commenti in inglese | — | 12 | `5836449` |
| `benchmark/audit/*` | `--run` (periodo dal manifest), logging | — | 15 | `6574f20`, `544a70d` |
| `benchmark/analysis/*` | `--run <riferimento> --compare <confronto>`, ruoli neutri, output in `<run>/analysis/`, `md_table` unica, id degli eventi presi dai flag | run fisse nel codice; `md` duplicata | 4, 15 | `f332e79`, `26c2985`, `3aa4acc` |
| `models/model_nn.met_to_utc`, `fermi_data_tools._iso_to_met` | sostituite da `utils/fermi_time` | identiche su 2 238 398 bin e su tutto il catalogo trigger | 5 | `46b0cca` |
| `benchmark/baseline_doc.py` | `--run/--compare`, legge le cartelle di run, scrive anche il blocco d'esempio del README | — | 14, 15 | `43b6535`, `a35bd28`, `544a70d` |
| `requirements.txt` | pin tenuti per ciò che si importa e per le sue dipendenze; tolti keras-tuner, shap, numba, llvmlite, cloudpickle, seaborn, sqlalchemy; tabulate non aggiunto; tsfel/xgboost come commento | — | 19 | `9c6fa54` |
| `.gitignore` + untrack | dati, modelli, log fuori dal repo; `data/runs/*/*/{pred,trig}` ignorati | nessun file > 5 MB | 9, 18 | `e5603db` |
| `README.md`, `LICENSE`, `data/README.md` | README in inglese; crediti mantenuti; riga di copyright di Giovanni aggiunta | — | 10 | `8ce767a` |
| `docs/PROJECT_MAP.md`, `docs/BASELINE.md` | rimossi (confluiti) | sezione 9 | — | `d8fa9f4` |
| `docs/WORKING_RULES.md` | sezione "Stato dopo il consolidamento" | — | — | `ac820ec` |
| `docs/DATA_INVENTORY.md`, `docs/ORBIT_ANALYSIS.md`, `docs/BASELINE_2019.md`, `docs/RUNS.md` | rigenerati con gli strumenti nuovi (stessi numeri) | — | — | `c977a8e`, `f911a28`, `2465c0d` |
| `data/runs/2019-03-01_2019-06-30/*` | manifest, `results/`, `validation/`, `RESULTS.md` (e `analysis/` di engine-v2-seed1) versionati; v3 rigenerate | — | 14, 18 | `25c1fd8` |
| test | +16 test: settings e periodo, ripresa delle run, manifest/checksum, step 6, `event_start_met`, dry-run della pipeline, implementazione unica del tempo | un test per ogni correzione | — | vari |

Stato dei 19 difetti:

- risolti: 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 19;
- 9: risolto per il repo; i dati legacy restano su disco, ignorati (sezione 9);
- 18: le run e la metadata del bundle seed1 sono ora versionate; i pesi no, per scelta (> 5 MB).

**Difetto 17** (manifest):

- `parameters` viene scritto solo alla creazione della run e non è mai riscritto;
- una voce `model` descrive il bundle che ha prodotto le predizioni (anche quando sono riusate), con il seed letto dai metadati e lo sha256 del bundle;
- se i parametri registrati o il checksum del bundle non coincidono con quelli attuali, la run si ferma (`PipelineStop`);
- ogni esecuzione aggiunge una riga di storia: data, commit, step da eseguire all'avvio.

La voce spuria del 2026-10-04 07:41 in `engine-v2/manifest.json` (`train_seed: 1`) al momento del consolidamento non era più presente: il file coincideva con la versione versionata (mtime 15:02).

## 4. Struttura finale

```
pipeline/pipeline_bkg.py       entry point unico (Crupi: stesso nome e posto)
connections/utils/config.py    configurazione unica (Crupi: stesso file, ora senza date e senza costanti legacy)
connections/fermi_data_tools.py cataloghi GBM da HEASARC (Crupi)
utils/keys.py                  chiavi dei canali (Crupi)
utils/period.py                periodi inclusivi
utils/fermi_time.py            UTC <-> MET, unica implementazione
utils/run_options.py           impostazioni, modalità del modello, manifest
utils/logs.py                  logging unico, formato di Crupi
models/download_bkg.py         step 1 (Crupi)
models/preprocess.py           step 2 (Crupi)
models/model_nn.py             step 3, bundle (Crupi)
models/losses.py               loss personalizzate (Crupi, da models/utils/)
models/trigger.py, trigs/focus.py  step 4, Poisson-FOCuS (Crupi)
models/analyze.py              step 5 (Crupi)
models/localize_event.py, loc/ step 6, localizzazione PSO (Crupi)
models/event_classifier.py     step 6, regole euristiche di Crupi
models/flags.py                step 7, flag di post-processing
benchmark/validate.py          step 8, calcolo della validazione
benchmark/report.py            step 9, RESULTS.md e RUNS.md
benchmark/matching.py          abbinamento uno-a-uno
benchmark/reference/           tabelle 10 e 11 di Crupi (CSV)
benchmark/baseline_doc.py      docs/BASELINE_2019.md + esempio nel README
benchmark/audit/               data_inventory, engine_checks, compare_runs
benchmark/analysis/            orbit_analysis, zero_prediction, orbit_report (docs/ORBIT_ANALYSIS.md)
tests/                         104 test
docs/                          BASELINE_2019, RUNS, ORBIT_ANALYSIS, DATA_INVENTORY, DIFF_UPSTREAM, WORKLOG, questo report, legacy_crupi/
data/                          vedi data/README.md
```

`scripts/` di Crupi non esiste più: tutti i suoi file erano legacy non funzionanti (difetto 7). `pipeline/` contiene solo l'entry point.

## 5. Pipeline

**Step**:

1. download;
2. preprocess;
3. fondo NN;
4. FOCuS;
5. eventi;
6. localizzazione e classificazione (lenta; `--jobs`; si salta con `SKIP_LOCALIZATION`; ripetibile: se manca solo la classificazione, la localizzazione non viene rifatta);
7. flag;
8. validazione (catalogo GBM sempre; tabelle di Crupi solo se il periodo tocca 2019-03-01 → 2019-07-09);
9. resoconto.

**Salti**:

- uno step si salta se i suoi output esistono;
- gli step 8 e 9 si rifanno se sono più vecchi dei loro ingressi;
- lo stato viene ricalcolato prima di ogni step;
- se tutto è presente e coerente col manifest (periodo, versione, parametri, checksum del bundle), la pipeline va direttamente al riepilogo: 0.1 s di esecuzione dopo l'avvio di Python.

**USER SETTINGS**, in cima a `pipeline/pipeline_bkg.py`:

- `START_DATE`, `END_DATE`, `RUN_LABEL`, `TRAIN_SEED`, `FORCE_TRAIN`, `REUSE_BUNDLE`, `ALLOW_TRAINING`, `SKIP_DOWNLOAD`, `SKIP_LOCALIZATION`, `JOBS`;
- ognuna ha la sua variabile d'ambiente `DEEPGRB_<NOME>`, che ha priorità (`utils/run_options.settings_to_env`);
- nessuna data è scritta altrove nel codice: `tests/test_period.py` verifica che la configurazione non ne contenga;
- restano nella configurazione soltanto il periodo coperto da Crupi e quello del modello legacy, che sono metadati dei riferimenti, non impostazioni della run.

**Sicurezza**:

- bundle, pred/ e trig/ non vengono mai sovrascritti;
- una run etichettata nuova non riusa una cartella esistente; una esistente riprende solo gli step mancanti;
- `FORCE_TRAIN` richiede etichetta e seed, e si ferma se la run ha già predizioni.

Stampa reale (`DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py`, run completa; log anche in `logs/pipeline_2019-03-01_2019-06-30_seed1_20261004_170341.log`):

```
2026-10-04 17:03:41 INFO     ========================================================================
2026-10-04 17:03:41 INFO       DEEPGRB PIPELINE  2019-03-01 -> 2019-06-30  (122 days, engine v3)
2026-10-04 17:03:41 INFO       run folder : data/runs/2019-03-01_2019-06-30/engine-v3-seed1
2026-10-04 17:03:41 INFO       model      : resume  data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1
2026-10-04 17:03:41 INFO       label seed1, train seed -, jobs 4
2026-10-04 17:03:41 INFO       log        : logs/pipeline_2019-03-01_2019-06-30_seed1_20261004_170341.log
2026-10-04 17:03:41 INFO     ========================================================================
2026-10-04 17:03:41 INFO       -> manifest coherent: engine v3, period, parameters, bundle checksum 0eae86f65d97...
2026-10-04 17:03:41 INFO     Status of the run (✔ = output present, step skipped):
2026-10-04 17:03:41 INFO       ✔ 1 download CSPEC + POSHIST         data/cspec  [skipped (SKIP_DOWNLOAD)]
2026-10-04 17:03:41 INFO       ✔ 2 preprocess daily tables          data/bkg  [122/122 days]
2026-10-04 17:03:41 INFO       ✔ 3 neural background                data/runs/2019-03-01_2019-06-30/engine-v3-seed1/pred  [symlink to data/runs/2019-03-01_2019-06-30/engine-v2-seed1]
...
2026-10-04 17:03:41 INFO       ✔ 9 report                           data/runs/2019-03-01_2019-06-30/engine-v3-seed1/RESULTS.md
2026-10-04 17:03:41 INFO     All steps are complete and coherent with the manifest: nothing to do.
2026-10-04 17:03:41 INFO     SUMMARY
2026-10-04 17:03:41 INFO       events          : 136 (R 102, S 11, P 23)
2026-10-04 17:03:41 INFO       GBM catalog     : 67/120 triggers, GRB 59/78
2026-10-04 17:03:41 INFO       Crupi et al.    : known 70/71, unknown 21/24
2026-10-04 17:03:41 INFO       no counterpart  : 46
2026-10-04 17:03:41 INFO       steps executed  : none (all outputs present)
2026-10-04 17:03:41 INFO       total time      : 0.1 s
```

**Altre prove**:

- spostando `RESULTS.md` la pipeline riesegue solo lo step 9 ("Steps to run: 9", 0.2 s);
- con `DEEPGRB_START_DATE=2019-03-02 DEEPGRB_END_DATE=2019-03-03 DEEPGRB_SKIP_DOWNLOAD=1 ... --dry-run` mostra la run `data/runs/2019-03-02_2019-03-03/engine-v3`, le tabelle giornaliere 2/2 e "Steps to run: 3, 4, 5, 6, 7, 8, 9", senza scrivere nulla (lo stesso caso è in `tests/test_pipeline.py`);
- su un periodo nuovo senza bundle, lo step 3 si ferma con un messaggio finché non si imposta `ALLOW_TRAINING` o `FORCE_TRAIN`.

## 6. Formato di RESULTS.md e RUNS.md

`<run>/RESULTS.md` ha le stesse otto sezioni per ogni run; una sezione senza ingressi lo dichiara invece di sparire:

1. run, rete e parametri;
2. eventi;
3. catalogo GBM;
4. confronto con Crupi;
5. senza controparte e flag;
6. classificazione;
7. localizzazione;
8. anomalie del motore.

Le tabelle complete sono accanto, in `validation/` e `results/`. Estratto reale (`data/runs/2019-03-01_2019-06-30/engine-v3-seed1/RESULTS.md`):

```
| criterio (docs/WORKING_RULES.md §6) | misurato | esito |
|---|---|---|
| Noti di Crupi ritrovati ≥ 90% | 70/71 (98.6%) | ✔ |
| Tutti gli R e S noti ritrovati | 65/65 (100.0%) | ✔ |
| Inediti R+S ritrovati ≥ 90% | 15/16 (93.8%) | ✔ |
| Inediti complessivi ≥ 70% | 21/24 (87.5%) | ✔ |

Eventi senza controparte (46) per combinazione di flag:
| saa_edge_short_passage, saa_region_proximity | 17 |
| nessuno | 15 |
| saa_region_proximity | 12 |
| near_zero_prediction | 2 |
```

`docs/RUNS.md` ha una riga per run, con colonne:

- periodo, run, rete e seed;
- eventi R/S/P, GBM, GRB, Crupi noti e inediti, senza controparte;
- loc/class e link al resoconto.

Estratto reale:

```
| 2019-03-01 → 2019-06-30 | `engine-v3-seed1` | `model_2019-03-01_2019-06-30_seed1`, seed 1 | 136 (102/11/23) | 67/120 | 59/78 | 70/71 | 21/24 | 46 | ✔/✔ | RESULTS.md |
```

## 7. .gitignore, requirements, README

**`.gitignore`** (56 righe, riscritto):

- ignorati: dati grezzi e preprocessati, output del vecchio layout, `gbm_burst_catalog.db` (10 MB, ricostruibile da HEASARC), pesi e scaler dei bundle (resta versionato `metadata.json`), `pred`/`trig` delle run, archivi (salvo README e checksum), `logs/`, `*.tar.gz`, `*.log`, `data_test/`, `m_check/`, `benchmark/out/`, `benchmark/analysis/out/`;
- versionati: `benchmark/reference/*.csv`, `data/gbm_trig_catalog.csv` (4.2 MB) e `data/DeepGRB_catalog.csv`, manifest, `RESULTS.md`, `results/`, `validation/` e `analysis/` delle run, `docs/`;
- verifica con `git check-ignore` su 15 percorsi da ignorare e 7 da versionare: tutti come previsto;
- `git ls-files | xargs du`: nessun file oltre 5 MB; il più grande tracciato è `data/gbm_trig_catalog.csv` (4.2 MB).

**`requirements.txt`** (46 righe, 31 pin; prima 38):

- import verificati con `ast` su tutto il codice: numpy, pandas, scipy, astropy, gbm, tensorflow, sklearn, joblib, pyswarms, matplotlib;
- dipendenze verificate con `importlib.metadata`; basemap resta perché lo usa `gbm.plot`;
- tolti i pacchetti non importati e non richiesti da altri;
- **tabulate non aggiunto**: non è installato nell'env e non serve, perché le tabelle markdown sono scritte da `benchmark/report.md_table` (difetto 19);
- tsfel e xgboost solo come commento per la fase XGBoost.

**`README.md`** (158 righe, 9.3 kB, in inglese):

- versione consolidata mantenuta da Giovanni Pio Martello (Politecnico di Bari, tesi con la Prof.ssa Bissaldi, ReCaS Bari/Jupyter);
- crediti invariati, presi dal README originale: R. Crupi, G. Dilillo, E. Bissaldi, K. Ward, F. Fiore, A. Vacchi; link a github.com/rcrupi/DeepGRB e ai due articoli;
- `LICENSE` MIT con il copyright di Crupi e Dilillo invariato, più una riga per Giovanni;
- contenuti:
  - i 9 step;
  - requisiti;
  - USER SETTINGS ed esempi nohup;
  - cartelle e run;
  - come leggere RESULTS.md;
  - esempio della baseline, generato da `baseline_doc` tra i marcatori `BASELINE:START/END`;
  - perimetro;
  - cosa è cambiato;
  - lavori aperti.

`data/README.md` (24 righe) descrive cosa contiene `data/` e cosa è versionato.

## 8. Operazioni git

> I comandi remoti di questa sezione sono superati dalla sezione 11 (storia riscritta il 2026-10-05).

Commit locali, nessun push. Comandi locali usati:

```bash
git bundle create ../deepgrb_pre_consolidation.bundle --all
git rm / git rm --cached / git mv ...      # sezione 3
GIT_SEQUENCE_EDITOR="sed -i ..." git rebase -i e0e8da3   # vedi sotto
git branch main 2465c0d                    # dopo il commit di questo report: main = HEAD
```

Il **rebase locale** (non interattivo, prima di qualunque push) ha corretto tre commit che contenevano file in più:

- `m_check/` nel primo commit;
- `benchmark/analysis/out/` nel commit degli strumenti orbitali;
- due cancellazioni di documenti nel commit di `baseline_doc`.

**Incidente durante il rebase.** Riapplicando i `git rm --cached` di `e5603db`, git ha rimosso dal disco le copie di lavoro di 50 file tracciati in precedenza:

- il modello legacy `.h5` e lo scaler legacy;
- `gbm_burst_catalog.db` e i due CSV d'archivio;
- `data/results/frg_03-2019_07-2019/*.csv` e `benchmark/out/**`;
- `data_test/` e il symlink `pred` di `engine-v2-sens-tmax29`.

Sono stati ripristinati subito, byte per byte, dagli oggetti git (`git restore --source=e0e8da3 --worktree --pathspec-from-file=...`, senza toccare l'indice), e verificati con i checksum dell'archivio:

- `sha256sum -c` di `data/_archive_20261003/SHA256SUMS_results.txt`: tutti OK;
- `SHA256SUMS_inputs_inplace.txt`: tutti OK salvo `gbm_trig_catalog.csv`, ricostruito di proposito in Fase 1; la versione precedente in archivio ha il checksum registrato.

Le cartelle con file non tracciati (`data/results/*/plots`, `data/`) non sono state toccate. Dimensioni finali uguali a prima:

- cspec 18G, poshist 2.2G, bkg 6.1G;
- pred 3.1G, trig 2.7G, results 248M;
- nn_model 347M, runs 13G, data_test 2.5G.

**Strategia per `main`**:

- `fix/baseline-2019` parte da `thesis`, che parte da `master`, che contiene la storia di Crupi;
- verificato con `git merge-base --is-ancestor`: `upstream/master`, `origin/master`, `master`, `thesis`, `origin/thesis`, `origin/fix/baseline-2019` e il tag `baseline-2019-validated` sono tutti antenati di HEAD;
- `main` è quindi un **fast-forward** dello stato finale e la storia di Crupi resta raggiungibile;
- il bundle resta fuori dal repo.

**Comandi remoti, da eseguire solo con conferma esplicita di Giovanni** (nessuno è stato eseguito):

```bash
git log --oneline origin/fix/baseline-2019..main      # i commit nuovi
git push origin main
git tag -a v1.0-baseline -m "Consolidated DeepGRB, 2019 baseline validated" main
git push origin v1.0-baseline                          # baseline-2019-validated è già sul remote
git checkout main
git branch -d fix/baseline-2019 thesis
git push origin --delete fix/baseline-2019 thesis
# su GitHub: impostare main come branch di default
```

## 9. Dubbi, scelte, cose non fatte, lavori aperti

**Scelte**

- **PROJECT_MAP.md** non è stato rigenerato: descriveva lo stato *prima* del consolidamento. La struttura attuale è nel README e nella sezione 4, l'elenco dei difetti con la loro sorte nella sezione 3; l'originale resta nella storia git (`e0e8da3`).
- **BASELINE.md** era ridondante con il README (comandi) e con BASELINE_2019.md (riproduzione), quindi è stato rimosso. **DIFF_UPSTREAM.md** è stato tenuto, perché è l'unico posto in cui le differenze dal codice di Crupi sono classificate.
- **Lingua dei resoconti generati.** `RESULTS.md`, `RUNS.md` e `BASELINE_2019.md` sono in italiano, come gli altri documenti di lavoro; README e codice sono in inglese.
- **Analisi una tantum.** `zero_prediction.py` è stato tenuto perché alimenta `ORBIT_ANALYSIS.md` §5b; `lr_check.py` e `sensitivity_tmax.py` sono stati rimossi, con i risultati nel WORKLOG e la run `engine-v2-sens-tmax29`.
- **Run v2.** Flag, validazione e `RESULTS.md` sono stati aggiunti alle run v2 con gli strumenti attuali (nessun file esistente riscritto), così RUNS.md copre tutte le run 2019.
- **Ripresa delle run.** Una run esistente con pred/ e trig/ riprende gli step mancanti. Prima una run etichettata esistente bloccava sempre; ora blocca solo se è incompleta o se si chiede `FORCE_TRAIN`.
- **pyswarms.** La configurazione incrementale vuota (`LOG_CFG`) impedisce che riconfiguri il logging; `report.log` alla radice era prodotto proprio da pyswarms.
- **Rigenerazione di step 8 e 9.** Gli output di validazione e di report di una run possono essere rigenerati, perché sono derivati e deterministici. Quelli degli step 3–7 mai.
- **Manifest delle run v3.** La riga di storia registra gli step *da eseguire all'avvio*. Nelle run v3 lo step 4 compare ma è stato saltato, perché lo step 3 crea i symlink anche di trig/.

**Non fatto**

- Nessun push, nessun tag nuovo, nessuna cancellazione di branch: sono i comandi in attesa della sezione 8.
- Nessuno spostamento in archivio dei dati legacy su disco (`data/pred`, `data/trig`, `data/results`, `data_test/`, `seed1_files.tar.gz`, `connections/utils/m_check/`, `benchmark/out/`): sono ignorati da git e restano dove sono finché Giovanni non decide.
- `report.log` (prodotto da pyswarms prima della correzione) resta sul disco, ignorato.

**Lavori aperti**

- XGBoost (fase 6), 2024.
- Il controllo di convergenza manca nel bundle seed1, che lo precede: RESULTS.md mostra val_loss e MAE test/train.

## 10. Comandi di riproduzione

Dalla radice del repo, env `deepgrb_recas`:

```bash
python -m unittest discover -s tests -t .                       # 104 test
python -u pipeline/pipeline_bkg.py --dry-run                     # stato della run di default
# invarianza: spostare engine-v3-seed1 / engine-v3 in data/_archive_<data>/, poi
DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --jobs 4
DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --jobs 4
sha256sum data/runs/2019-03-01_2019-06-30/engine-v3*/results/*.csv
cmp data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_classified.csv data/_archive_20261004/engine-v3-seed1/results/events_classified.csv
# run v2 (step 7-9 fuori dalla pipeline)
python -m models.flags --run data/runs/2019-03-01_2019-06-30/engine-v2
python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v2
python -m benchmark.report --run data/runs/2019-03-01_2019-06-30/engine-v2
# documenti
python -m benchmark.baseline_doc --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --compare data/runs/2019-03-01_2019-06-30/engine-v3
python -m benchmark.analysis.orbit_analysis --run data/runs/2019-03-01_2019-06-30/engine-v2-seed1 --compare data/runs/2019-03-01_2019-06-30/engine-v2
python -m benchmark.analysis.zero_prediction --run data/runs/2019-03-01_2019-06-30/engine-v2-seed1 --compare data/runs/2019-03-01_2019-06-30/engine-v2
python -m benchmark.analysis.orbit_report --run data/runs/2019-03-01_2019-06-30/engine-v2-seed1 --compare data/runs/2019-03-01_2019-06-30/engine-v2
python -m benchmark.audit.data_inventory --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1
python -m benchmark.report --index
# controlli finali
python -m compileall -q connections utils models pipeline benchmark tests
git ls-files -z | xargs -0 du -k | awk '$1 > 5120'               # vuoto
```

## 11. Resoconto completo e pulizia della storia (2026-10-05)

### 11.1 Resoconto automatico (`benchmark/report.py`, step 9)

| cosa | dove | numeri di engine-v3-seed1 (identici in engine-v3-verify1) |
|---|---|---|
| Matrice di confusione contro le classi **tentative** di Crupi: conteggi, % per riga (recall), % per colonna (precision), recall/precision/supporto per classe, accuracy | `RESULTS.md` §6.1, `validation/classification_metrics.csv` | 87 eventi con classe univoca; riga GRB 68/0/0/1/1; accuracy 75/87 (86.2%); GRB recall 97.1%, precision 90.7% |
| Tipo di trigger GBM × classe predetta (conteggi, % per riga) e concordanza con la mappatura **ipotetica** GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP), UNCERT→UNC | `RESULTS.md` §6.2, `validation/gbm_type_vs_class.csv`, `gbm_type_concordance.csv` | 62/67 (92.5%): GRB 57/59, SFLARE 4/5, LOCLPAR 1/3; legacy 63/68 |
| Controllo del join: ogni trigger abbinato cade nella finestra dell'evento a cui punta `event` (margine 8.192 s; change point al massimo `t_max` + 1 bin prima di `start_met`), altrimenti `JoinError` | `benchmark/report_tables.check_gbm_join` | superato su tutte le 6 run |
| Elenchi per nome: GRB e trigger non-GRB del catalogo GBM (esito rivelato / mancato / senza dati, evento, classe), eventi di Crupi (ritrovato / non ritrovato + diagnosi, classe) | `RESULTS.md` §9, `validation/list_gbm_grb.csv`, `list_gbm_other.csv`, `list_crupi_events.csv` | GRB: 59 rivelati, 19 mancati, 15 senza dati; non-GRB: 8 rivelati, 34 mancati, 8 senza dati; Crupi: 91 ritrovati, 4 no |

Note sul resoconto:

- Il tipo GBM viene dichiarato per quello che è: **non** è la natura fisica dell'evento.
- Il classificatore continua a non leggere colonne del catalogo (`tests/test_classifier.py`).
- 11 nuovi test su dati sintetici (`tests/test_report_tables.py`): percentuali per riga e per colonna, metriche per classe, join corretto e join sbagliato, elenchi per nome.
- Sulle run esistenti è stato rigenerato solo lo step 9; i checksum di `BASELINE_2019.md` §6 sono invariati.
- `pipeline/pipeline_start.py` esegue gli step 3–9 su una cartella nuova, con una copia del bundle; il `--dry-run` non copia nulla. È documentato nel README.
- La run `engine-v3-verify1` ha `pred/bkg.csv`, `trig/trig.csv`, `results/` e i CSV di validazione identici byte per byte a quelli di engine-v3-seed1.

### 11.2 Pulizia dei riferimenti

Backup prima di iniziare: `git bundle create ../deepgrb_pre_scrub2.bundle --all` (810 MB, fuori dal repo) e tag **locale** `backup/pre-scrub2` (`9e8e07e`), da non pubblicare. Il bundle e quel tag contengono ancora i riferimenti originali.

| trovato (inventario in sola lettura) | intervento |
|---|---|
| Il vecchio file delle regole di lavoro alla radice del repo, in 4 versioni della storia | rinominato in `docs/WORKING_RULES.md` in **tutta** la storia (`git filter-repo --path-rename`); intestazione e §7 riscritte in forma neutra; il file locale con quel nome, se serve, è escluso con `.git/info/exclude` (non con `.gitignore`, che è tracciato e avrebbe reintrodotto il nome) |
| 61 righe distinte in 846 blob storici: riferimenti a quel file (`… §2`, `§6`, …) in codice, test, documenti e `RESULTS.md` generati | `--replace-text`: il nome del vecchio file → `docs/WORKING_RULES.md`, in ogni versione |
| 3 frasi che nominavano lo strumento nelle regole di lavoro ("Documento operativo per …", "analisi della repo (…)", "delegate a …") | riformulate in ogni versione; il contenuto tecnico è invariato |
| 2 righe di messaggi di commit con il nome del file | `--replace-message` con le stesse regole |
| Righe di attribuzione (`Co-Authored-By`, righe di sessione, "Generated with"): **nessuna** (la riscrittura precedente le aveva già tolte) | — |
| Autori o committer diversi dalle persone del progetto: **nessuno** | — |
| Tag annotati `baseline-2019-validated`, `v1.0-baseline`: messaggi senza riferimenti | ricreati da filter-repo sui commit corrispondenti (`e4675cc`, `a41e21d`), stesso messaggio e stesso tagger |
| Hash citati nei documenti, riferiti a commit che la riscrittura precedente aveva già cambiato | tradotti con `.git/filter-repo/commit-map` (che concatena le due riscritture) in un commit finale; tabella completa in `docs/COMMIT_MAP.md`. Restano originali i due commit di Crupi citati (`0d7d82c`, `85542b5`), validi upstream, e `bf188c2`, intermedio mai pubblicato |
| Remote `origin` rimosso da filter-repo | ricreato (`https://github.com/johnh-04/DeepGRB.git`), senza fetch |

**Cose emerse durante il lavoro**

- La riscrittura precedente (fatta prima di questo lavoro) aveva già cambiato gli hash di 131 commit di Crupi e degli altri autori originali: aveva tolto le firme GPG e aggiunto l'a capo finale ai messaggi. Tree, autore e testo sono identici: per esempio la punta di upstream `0d7d82c` è diventata `18bfe63`, con lo stesso tree `14430d4`. Il `master` **sul remoto** è ancora quello originale (`0d7d82c`); il `master` locale (`01bbd8c`) non è stato toccato da questa pulizia (verificato: nessun suo commit conteneva riferimenti).
- Sul remoto `main` era un commit più avanti di quello locale: `5ad3296`, modifica del README fatta su GitHub ("master's thesis" → "bachelor's thesis"). Per non perderla col push forzato è stata riportata su `main` locale (commit `c48cb59`, autore Giovanni Pio Martello, data originale).
- Hash dentro file generati (`manifest.json`, `metadata.json`, `summary.json`, `RESULTS.md`): non riscritti a mano, si riferiscono ai commit precedenti alla riscrittura. Si traducono con `docs/COMMIT_MAP.md`.

**Non fatto**

- Nessun push e nessuna modifica al remoto.
- `master`, `fix/baseline-2019` e `thesis` restano locali e non vanno pubblicati (`fix/baseline-2019` = `a41e21d`, `thesis` = `bf0d7a1`, `master` = `01bbd8c`).
- Le copie del vecchio contenuto restano raggiungibili: nel bundle di backup, nel tag locale `backup/pre-scrub2` e su GitHub per SHA finché il supporto non le elimina.

### 11.3 Verifica

`$NOMI` è il pattern dei nomi da escludere (lo strumento e il suo produttore, in OR, senza distinzione di maiuscole), definito nella shell e non scritto nel repo.

```
$ git log --exclude=refs/tags/backup/* --all --format=%B | grep -ic "$NOMI"
0
$ git log --all --format=%B | grep -ic "$NOMI"          # include il tag locale di backup
2
$ git grep -il "$NOMI" $(git rev-list main) | wc -l
0
$ git grep -il "$NOMI" $(git rev-list fix/baseline-2019 thesis master) | wc -l
0
$ git ls-files | grep -ic "$NOMI"
0
$ git log --exclude=refs/tags/backup/* --all --format=%B | grep -ic "co-authored-by\|-session:\|generated with \["
0
$ tag annotati: baseline-2019-validated -> e4675cc, v1.0-baseline -> a41e21d, 0 occorrenze
$ git diff --name-status backup/pre-scrub2 main -- data benchmark | cut -f1 | sort | uniq -c
     53 A          # nuove tabelle di validation/ e la run engine-v3-verify1
     10 M          # baseline_doc.py, report.py, validate.py (2 commenti), 2 README d'archivio, 5 RESULTS.md
$ CSV preesistenti modificati sotto data/runs: 0;  results/ modificati: 0 (5 aggiunti, tutti di engine-v3-verify1)
$ checksum di docs/BASELINE_2019.md §6 ricalcolati sui file: 16 OK; §6 identica a quella del backup
$ python -m unittest discover -s tests -t .
Ran 115 tests ... OK
$ python -m compileall -q connections utils models pipeline benchmark tests
exit 0
$ DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --dry-run
  -> manifest coherent: engine v3, period, parameters, bundle checksum 0eae86f65d97...
  ✔ 1 … ✔ 9; All steps are complete and coherent with the manifest: nothing to do.
  events 136 (R 102, S 11, P 23); GBM 67/120; Crupi known 70/71, unknown 21/24; total time 0.1 s (≈1 s con l'avvio di Python)
$ git ls-files -z | xargs -0 du -k | awk '$1>5120' | wc -l
0
```

### 11.4 Pubblicazione (da eseguire solo dopo la conferma di Giovanni)

Stato del remoto (`git ls-remote origin`, 2026-10-05):

- `main` = `5ad3296`;
- `master` = `0d7d82c` (originale di Crupi);
- `baseline-2019-validated` → `c670a84`;
- `v1.0-baseline` → `a30bbf2`.

```bash
git push --force-with-lease=main:5ad3296a9230fdc0246067149f094cb97249c1ec origin main
git push --force origin baseline-2019-validated v1.0-baseline
# NON usare --tags/--all: pubblicherebbero backup/pre-scrub2, master, thesis, fix/baseline-2019
```

Poi su GitHub:

1. **Branch predefinito**: Settings → Branches → `main`. Oggi `HEAD` del remoto punta già a `main`: va solo verificato.
2. **Commit vecchi ancora raggiungibili**: restano accessibili via URL per SHA (es. `5ad3296`, `a30bbf2`) e nelle viste in cache. Va aperta una richiesta al supporto GitHub (modulo "Remove data from a repository", cancellazione dei commit non più referenziati e delle viste in cache), indicando il repository `johnh-04/DeepGRB`.
3. **Altri cloni** (per esempio quello locale su macOS) vanno riallineati con `git fetch origin && git reset --hard origin/main` oppure riclonati, altrimenti un push successivo reintroduce la vecchia storia.
