# Baseline 2019: come riprodurla

Questa guida rigenera la baseline 2019 di DeepGRB (motore di Crupi et al. 2023) e il report di validazione. Tutte le cifre del report sono calcolate dal codice. Il riepilogo dei risultati è in [`benchmark/out/REPORT.md`](../benchmark/out/REPORT.md); la storia delle correzioni è in [`docs/WORKLOG.md`](WORKLOG.md).

## 1. Ambiente

```bash
conda activate deepgrb_recas        # Python 3.9.23
cd DeepGRB                           # tutti i comandi partono dalla radice del repo
```

Versioni usate: numpy 1.26.4, pandas 1.5.3, TensorFlow 2.20.0, Keras 3.10.0, scipy 1.13.1, scikit-learn 1.6.1, gbm-data-tools 1.1.1, astropy 6.0.1, pyswarms 1.3.0 (vedi `requirements.txt`). Non servono GPU né rete, salvo per scaricare dati mancanti o addestrare un nuovo modello.

## 2. Comandi (periodo 2019-03-01 → 2019-06-30)

| # | Comando | Cosa produce | Tempo misurato* |
|---|---|---|---|
| 0 | `python -m unittest discover -s tests -t .` | 58 test sulle funzioni reali | ~25 s |
| 1 | `python pipeline/pipeline_bkg.py` | step 1–5 in `data/runs/2019-03-01_2019-06-30/engine-v2/` | ~11 min (download e preprocess saltati se i dati ci sono già) |
| 2 | `python -m benchmark.audit.engine_checks` | `results/engine_checks.md` (fondo, SAA, sigma) | ~2 min |
| 3 | `python -m benchmark.classify --jobs 4` | `results/events_table_loc.csv`, `results/events_classified.csv` | ~6 min |
| 4 | `python -m benchmark.validate` | `benchmark/out/REPORT.md` + tabelle CSV | ~2 min |
| opz. | `python -m benchmark.audit.sensitivity_tmax` poi `python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v2-sens-tmax29 --out benchmark/out/sensitivity_tmax29` | sensibilità a dmax = 120.4 s | ~7 min |
| opz. | `python -m benchmark.audit.data_inventory` | `docs/DATA_INVENTORY.md` | ~1 min |

\* Misurati il 2026-10-03 su un nodo con 96 core e 754 GB di RAM; la pipeline usa al massimo 4 worker. Memoria misurata: 4.6 GB di RSS durante lo step 3. Tempi e memoria su un nodo ReCaS da 4 vCPU/16 GB **non sono stati misurati**; la classificazione con `--jobs 4` tiene in memoria una copia delle matrici frg/bkg per worker (con 16 GB, se serve, usare `--jobs 2`).

Se un output esiste già, lo step viene saltato. Per rifare uno step **sposta** (non cancellare) la sua cartella in `data/_archive_<data>/` e rilancia.

### Risultato atteso

Con i dati e il modello attuali la run deve dare: 179 trigger → **144 eventi** (R 105, S 18, P 21); Crupi noti **70/71**, inediti **21/24**; GRB rivelati 60/78 (15 senza dati per la SAA); classificazione euristica (baseline) sugli eventi abbinati: regola GRB precision 0.91 / recall 0.97, etichetta singola compatibile con Crupi in 79/91 casi. Le tabelle CSV di `benchmark/out/` devono essere identiche byte per byte (verificato rieseguendo la validazione).

## 3. Dati e cache

```
data/
  cspec/, poshist/                 file grezzi Fermi (download idempotente)
  bkg/YYMMDD.csv                   tabelle giornaliere (rate + feature orbitali)
  gbm_trig_catalog.csv             catalogo trigger GBM (intervallo time→end_time + istante trig_met)
  gbm_burst_catalog.db             Burst Catalog (T90)
  nn_model/bundles/<nome>/         rete + scaler.joblib + metadata.json (periodo, seed, versioni)
  runs/<start>_<end>/engine-v<N>/  output degli step 3–5 per periodo e versione del motore
    manifest.json                  parametri, commit git, versioni, storia delle esecuzioni
    pred/frg.csv, pred/bkg.csv     rate osservati e fondo previsto (UTC, NaN = mascherato)
    trig/trig.csv, trig/offset.csv significatività e offset FOCuS per canale
    results/                       triggers_table, events_table, *_loc, *_classified, engine_checks.md
  _archive_YYYYMMDD/               stati congelati o invalidati (mai cancellati)
```

`ENGINE_VERSION` (in `connections/utils/config.py`) va incrementata a ogni modifica che cambia predizioni, trigger o eventi: la nuova versione scrive in una cartella nuova e non riusa risultati prodotti da codice più vecchio.

## 4. Parametri (stampati all'avvio e salvati nel manifest)

Bin 4.096 s; bande NaI 28–50, 50–300, 300–500 keV; rete 60→2048→2048→1024→36 (MAE, Nadam, 64 epoche, batch 2048, split 52/23/25); esclusione SAA ±150 bin attorno ai buchi > 500 s; FOCuS su rate con mu_min 1.2 e t_max 50 bin; trigger 3σ in r1 su ≥ 1 rivelatore; merge 600 s; S = Σ(N−B)/√ΣB sui rivelatori scattati con taglio sui quantili; C = max(S_r0, S_r1, S_r2); tier CE R/S/P. Per le tre discrepanze tra paper e codice upstream vedi docs/WORKING_RULES.md §2.

## 5. Un altro periodo (es. 2024)

Il periodo si sceglie con variabili d'ambiente; ogni periodo ha la sua cartella in `data/runs/`, quindi non c'è nessuna collisione di cache.

```bash
export DEEPGRB_START_DATE=2024-03-01 DEEPGRB_END_DATE=2024-06-30
python pipeline/pipeline_bkg.py                          # scarica, preprocessa, poi si ferma: manca il modello
DEEPGRB_ALLOW_TRAINING=1 python pipeline/pipeline_bkg.py # addestra una rete per il periodo (GPU consigliata, es. H100 MIG)
python -m benchmark.classify --jobs 4
```

Il modello legacy del 2019 viene usato solo per il periodo su cui è stato addestrato. Gli altri periodi richiedono un training esplicito (`DEEPGRB_ALLOW_TRAINING=1`), che salva un bundle con il seed (`TRAIN_SEED` nella pipeline). La validazione contro Crupi esiste solo per il 2019: `benchmark/validate.py` per un altro periodo produce la parte A (catalogo GBM) e riporta le tabelle di Crupi come fuori finestra.

## 6. Limiti noti

- La rete è una ri-esecuzione della ricetta di Crupi (addestrata il 2026-09-21), non la sua rete originale, che non è disponibile. Ne seguono 52 eventi senza controparte né GBM né Crupi (diagnosi per evento nel report). La stabilità rispetto al seed non è stata misurata (richiede nuovi training).
- Classificatore: è la baseline euristica di Crupi (soglie da decision tree rifinite a mano), da superare con XGBoost (docs/WORKING_RULES.md, Fase 6). Mancano la regola FP e le feature `fe_*` (tsfel, branch upstream `ric_review_28062023`).
- Script di analisi in `scripts/` e `pipeline/script_to_latex.py`/`manual_label.py`: legacy, usano i vecchi path e le etichette posizionali; non fanno parte della baseline.
