# Differenze del fork rispetto a upstream (rcrupi/DeepGRB)

Fase 0, audit in sola lettura. Data: 2026-10-03. Branch: `fix/baseline-2019`.

- Upstream: `upstream/master` = `0d7d82c` (coincide con il merge-base del fork).
- Fork: `HEAD` = `bf0d7a1` (branch `thesis`).
- Comando: `git diff upstream/master HEAD -- <file>`, più la lettura completa dei file nelle due versioni (le riscritture sono quasi totali, il diff riga per riga non è leggibile).

Classificazione:
- **Intenzionale**: porting (Keras 3, pandas 2, Python 3.9), adattamenti HPC/path, guardie difensive. Nessun effetto sui risultati scientifici.
- **Regressione**: cambia il comportamento rispetto al codice del paper o lo rompe.
- **Da decidere**: il codice upstream stesso differisce dal testo del paper; serve una decisione esplicita (§4 regola 9 di docs/WORKING_RULES.md).

## 0. Storia del fork sui file chiave

| Commit | Data | Cosa tocca nei file chiave |
|---|---|---|
| `01bbd8c` | 2026-09-19 | Porting fedele: `df.append` → `pd.concat`, `.ckpt` → `.keras`, `loss_weights=1.0`, `set` → `list` negli indici, `makedirs`. Nessun cambio di logica. |
| `477a950` | 2026-09-20 | Nessun file in `models/`. |
| `5d12562` | 2026-09-23 | `analyze.py` (5 righe), `trigger.py` (parallelizzazione). |
| `bf0d7a1` | 2026-10-03 | **Riscrittura completa** di `analyze.py`, `model_nn.py`, `preprocess.py`, `trigs/focus.py`. |

Conseguenza: gli artefatti su disco hanno provenienze diverse (vedi §6). In particolare il modello e `pred/` sono stati prodotti da codice equivalente a upstream (`01bbd8c`), non dal `model_nn.py` attuale.

## 1. `models/trigs/focus.py`

| # | Differenza | Classe | Note |
|---|---|---|---|
| F1 | `Curve.evaluate` ritorna 0 se `mu <= 0`; `xmax` ritorna 1.0 se `|b| < 1e-12` | Intenzionale | Guardie difensive. Con `a > 0` e `b < 0` (unico caso raggiunto) il risultato è identico. |
| F2 | `ab_crit is not None` invece di `ab_crit and …` | Intenzionale | Equivalente (`ab_crit` non è mai 0 per `mu_min > 1`). |
| F3 | Type hints, `set` → `build_focus_runner` (con alias `set`) | Intenzionale | |

**Esito: equivalente.** Aggiornamento, pruning, `mu_min`, `t_max` e reset sui NaN coincidono con upstream.

## 2. `models/trigger.py`

| # | Differenza | Classe | Note |
|---|---|---|---|
| T1 | Esecuzione parallela con joblib (max 4 worker) | Intenzionale | HPC. Stessi risultati per canale. |
| T2 | CSV scritti a precisione piena invece di `float_format='%.2f'` | Intenzionale | Più precisione; nessun effetto sulla soglia 3σ. |
| T3 | Path via `pathlib`, `makedirs` | Intenzionale | |
| T4 | Ingresso a FOCuS: colonne di `frg`/`bkg` così come sono, cioè **rate** (conteggi/s) | Da decidere (§5.4) | **Identico a upstream**: anche upstream passa i rate (`preprocess.py` salva `lightcurve.rates`). Non è una regressione del fork. Se il paper intende conteggi per bin, è una scelta da prendere esplicitamente: cambierebbe la scala delle σ di √4.096 ≈ 2.02. |

**Esito: equivalente.** Il problema dello step 4 (sanificazione `fillna(10)`) sta in `pipeline/pipeline_bkg.py`, non qui (vedi §7).

## 3. `models/preprocess.py`

| # | Differenza | Classe | Note |
|---|---|---|---|
| P1 | Cerca il POSHIST anche in `data/poshist/`, oltre che in `cspec/` | Intenzionale | Layout delle cartelle su ReCaS. |
| P2 | `n_jobs` limitato a 4 | Intenzionale | HPC. |
| P3 | Rimosso il warning sui NaN nella tabella giornaliera e quello sulla dimensione dei canali (`> 10` campioni di differenza) | Regressione minore | Solo diagnostica; utile ripristinarla. |
| P4 | Bande, rebin 4.096 s, `rates`, feature POSHIST | — | Identici. |

**Esito: equivalente** salvo la diagnostica (P3).

## 4. `models/model_nn.py`

| # | Differenza | Classe | Impatto |
|---|---|---|---|
| M1 | **`predict`: `Time(met, format="fermi").datetime` invece di `.utc.to_datetime()`**. Il formato `fermi` ha scala TT. | **Regressione — alta** | Tutti i `timestamp` sarebbero **+69.184 s** rispetto a UTC. Verificato: MET 573284724.164 → 05:46:28.35 (fork) contro 05:45:19.16 (upstream, e anche Crupi). Il codice attuale non ha ancora prodotto file: `pred/` su disco è in UTC. **Non era nella lista di docs/WORKING_RULES.md.** |
| M2 | `train(bool_train=False)` cerca `model_<start>_<end>.keras`; upstream cercava `.h5` e sceglieva quello con la loss minima | Regressione (§5.7) | Il modello su disco (`model_03-2019_07-2019_4.4_2026-09-21.h5`) non si può ricaricare. |
| M3 | Lo scaler viene rifittato ogni volta e non viene salvato | Regressione (§5.7), già presente upstream | Upstream fa lo stesso. Va comunque corretto. |
| M4 | `prepare`: finestra dei file `[start01, end31]` (mese finale incluso); upstream `[start01, end01)` (mese finale escluso) | Regressione | Con i dati di luglio presenti, il training includerebbe tutto luglio, oltre il 9 luglio. Da allineare alle date esplicite del §5.5. |
| M5 | Training: `random_state` 0→42; `validation_split` 0.3→0.2; EarlyStopping `patience` 32→20 senza `min_delta=0.01`; **scheduler del learning rate rimosso** (upstream: ×12.5 nelle prime 4 epoche, ×2 fino alla 12, ×0.5 dopo); Nadam `beta_2` 0.99→0.999; nessun file `.txt` con le metriche per canale | Regressione | La configurazione di training non è più quella del paper. Non tocca il modello attuale (addestrato con `01bbd8c`). |
| M6 | Default `loss_type='median'` (upstream `'mean'`) | Intenzionale/innocua | La pipeline passa sempre `'mean'`. |
| M7 | `predict`: maschera SAA `range(i−150, i+150)` sull'indice prima del buco; upstream `range(max(ind−150, min_idx), min(ind+150, max_idx))` sull'indice dopo il buco, con clip al primo e all'ultimo buco | Intenzionale/trascurabile | 1 bin di differenza per buco. Spiega il pattern osservato su disco (299/300 bin, primo buco mascherato a metà) → `pred/` viene dal codice upstream-like. |
| M8 | `predict`: in `bkg` mette a NaN solo le colonne dei rate (upstream: tutta la riga, compresi `met` e `timestamp`) | Intenzionale (miglioramento) | Upstream perde `met`/`timestamp` in `bkg` nelle zone mascherate (osservato su disco: 310 500 NaN in `bkg.met`). |
| M9 | `predict`: **rimosso** l'azzeramento dei conteggi nulli (upstream mette a NaN `frg == 0` e il `bkg` corrispondente) | Regressione | Ci si affida allo `zero_mask` di `run_trigger`, ma lo step 4 della pipeline lo rende inefficace (§7). |
| M10 | `±150` **bin** attorno ai buchi > 500 s (≈ ±614 s) | Da decidere (§5.3) | **Identico a upstream** (commento upstream: "time_to_del*4 seconds"). Il testo del paper (come riportato in docs/WORKING_RULES.md) dice ±150 s. Non è una regressione del fork. |
| M11 | Rimossi `plot`, `explain` (SHAP), ricerca iperparametri (keras-tuner), `model_pretrain` nel training | Intenzionale | Non usati dalla pipeline. |
| M12 | Esclusione dei trigger GBM: `<`/`>` invece di `<=`/`>=` | Intenzionale | Differenza solo sul bordo. |

## 5. `models/analyze.py`

| # | Differenza | Classe | Impatto |
|---|---|---|---|
| A1 | **`tableize` rimossa**: `events_table` non contiene più `sigma_r0/r1/r2`, `qtl_cut_*`, `start_times_offset`, `end_times` | **Regressione — alta** (§5.1) | Le sigma per evento non vengono più calcolate. Upstream: `events_table = tableize(events, …)` *dopo* il merge, con `sigma_type='SC_poisson'`: S = Σ(N−B)/√ΣB sui rivelatori scattati di quella banda, sulla finestra con offset, massimizzata su 21 tagli di quantile (0, 0.05, …, 1) dei residui. |
| A2 | **Offset FOCuS rimosso da `Segment`**: upstream estende l'inizio a `start + min(offset) + 1` e calcola le sigma su `fermi_offset`/`nn_offset` | **Regressione — alta** | Cambia sia la finestra delle sigma sia l'inizio dell'evento (`start_times_offset`). |
| A3 | **Convenzione degli indici**: fork `iloc[start:end]` (fine esclusa) e `end_met = met[ultimo bin]`; upstream `loc[start:end]` (fine inclusa) con `end` = ultimo bin + 1 | **Regressione — media** | Le durate del fork sono **più corte di 4.096 s**. Verificato su disco: evento 0 = 77.83 s nel fork contro 81.92 s nella `triggers_table` upstream. Eventi di un solo bin hanno durata 0.0 s (es. 2019-05-25 00:45:54). Crupi riporta 88.06 s per `2019_1` (convenzione upstream). |
| A4 | Rimossi `check_against_gbmcatalogs`, `GBMtrigger`, il plot greenred, i plot e gli export per evento/burst, `stat_table.csv`, `summary.txt` | Regressione | Si perde la statistica GRB detected/undetected/missing del paper (base della Validazione A). |
| A5 | Parametri `type_time`, `type_counts`, `bln_plot` accettati ma ignorati | Regressione minore | Fallimento silenzioso. |
| A6 | `fetch_triggers`: stessa logica (solo banda r1, ≥ `MIN_DET_NUMBER`, veto `< MAX_DET_NUMBER` con slice a fine inclusa) | Equivalente | `MAX_DET_NUMBER = 13` anche in upstream: il veto non scatta mai (12 NaI). Vedi §5.8. |
| A7 | `merge`: identica | Equivalente | |
| A8 | Ritaglio del catalogo e maschera `trigs`: `>=`/`<=` invece di `>`/`<` | Intenzionale/trascurabile | Differenza solo sul bordo. |
| A9 | `sigma_residual` (MAD) calcolata ma mai usata | Neutra | Anche in upstream serviva solo per l'opzione `SC_residual`. |

## 6. Provenienza degli artefatti su disco (`data/`)

| Artefatto | Prodotto da | Evidenza |
|---|---|---|
| `bkg/*.csv` (122) | `preprocess.py` equivalente a upstream | Logica identica (§3). |
| `nn_model/model_03-2019_07-2019_4.4_2026-09-21.h5` + `.txt` | `model_nn.py` di `01bbd8c` (= upstream) | Nome con loss e data, file `.txt` di metriche: formati che il codice attuale non produce. |
| `pred/frg_*.csv`, `pred/bkg_*.csv` | `predict` di tipo upstream (21 set), **poi sovrascritti** il 1° ottobre dallo step 4 | Maschera SAA con il pattern upstream (M7); `bkg.met` NaN (M8); **0 NaN** nelle colonne dei rate e 310 500 valori = 10.0 per canale (= 1 035 buchi × 300 bin); colonna `event` aggiunta in `frg`. Timestamp in UTC. |
| `trig/trig_*.csv`, `trig/offset_*.csv` | `trigger.py` del fork, sugli input già sanificati | 0 NaN su 2 238 398 righe → FOCuS non ha mai azzerato le curve ai bordi SAA; precisione piena (non `%.2f`). |
| `results/.../triggers_table.csv`, `stat_table.csv` (21 set) | `analyze.py` upstream-like | Colonne di `tableize`: 177 trigger prima del merge. |
| `results/.../events_table*.csv` (2 ott) | `EventAnalyzer` del fork + step 6/7 | Niente colonne di `tableize`; sigma unite da `triggers_table` per `trig_ids` (§5.1). |

**Implicazione:** gli input `pred/frg_*` e `pred/bkg_*` originali (con NaN) non esistono più. La maschera si può ricostruire in modo deterministico (le celle a 10.0 coincidono in `frg` e `bkg`, e nessun valore reale è esattamente 10.0 nei canali controllati), ma in Fase 2 è più pulito rigenerare `pred/` in una cache nuova (vedi WORKLOG).

## 7. Fuori dai 5 file chiave, ma rilevante (`pipeline/pipeline_bkg.py`)

| # | Differenza rispetto a upstream | Classe |
|---|---|---|
| X1 | Step 4: `fillna(10.0)`, valori `<= 0` → 1.0, poi **riscrittura di `frg`/`bkg`** (§5.3) | Regressione — alta (verificata su disco) |
| X2 | Parametri NN della pipeline: `bs=8192` (upstream `2048`); gli altri (`units=2048, epochs=64, lr=0.0008, dropout=0.02`) coincidono | Regressione (rispetto al paper) |
| X3 | `t_max=50` bin (= 204.8 s) in **entrambi**; il paper (secondo docs/WORKING_RULES.md) dà `dmax = 120.4 s` (≈ 29.4 bin) | Da decidere |
| X4 | Download: la pipeline cerca la colonna `day`, ma `download_spec` restituisce `id`/`tStart` (§5.6) | Regressione |
| X5 | Step 6/7: arricchimento con il catalogo, classificazione con leakage, benchmark con 1200 s e 153 giorni (§5.2, §5.5) | Regressione |

## 8. Riepilogo

- **Equivalenti a upstream:** `focus.py`, `trigger.py`, `preprocess.py` (salvo la diagnostica).
- **Regressioni ad alto impatto:** M1 (timestamp TT, **nuova**), A1 + A2 (sigma e offset), A3 (durate −4.096 s, **nuova**), X1 (sanificazione).
- **Da decidere con te (§4 regola 9):** T4 (rate o conteggi a FOCuS), M10 (±150 bin o ±150 s), X3 (`t_max` 50 bin o 120.4 s). In tutti e tre i casi il nostro codice **coincide con upstream** e differisce dal testo del paper.
