# WORKLOG — baseline 2019

Ogni voce: cosa è cambiato, perché, risultato misurato (valori reali dai file).

---

## 2026-10-03 — Fase 0: audit e congelamento (nessuna modifica funzionale)

### Ambiente
- Branch `fix/baseline-2019` creato da `thesis` @ `bf0d7a1`.
- Env conda `deepgrb_recas`: Python 3.9.23, numpy 1.26.4, pandas 1.5.3, TensorFlow 2.20.0, Keras 3.10.0, scipy 1.13.1, scikit-learn 1.6.1, gbm-data-tools 1.1.1. `pytest` non installato.
- Remote `upstream` = `https://github.com/rcrupi/DeepGRB.git`; `upstream/master` = `0d7d82c` = merge-base del fork.

### Test esistenti
- `models/tests/test_merge_events.py`: 5/5 PASSED.
- `models/tests/test_trigger_condition.py`: 8/8 PASSED.
- Limite: entrambi testano **copie locali** di `merge`/`fetch_triggers`, non le funzioni di `models/analyze.py` (regola 7, da sistemare in Fase 2).
- `test_pipeline.py` **non eseguito** di proposito: allo step 4 riscrive `data_test/pred/*` (violerebbe la regola 6) ed è un run end-to-end, non un test.

### Riferimenti
- `benchmark/reference/crupi_2019_known.csv`: 74 righe, CE = 64 R / 4 S / 6 P, id unici, 0 tempi NaN, dal 2019-03-03 05:45:19 al 2019-07-08 08:45:14.
- `benchmark/reference/crupi_2019_unknown.csv`: 25 righe, CE = 13 R / 3 S / 9 P, id unici, 0 tempi NaN, dal 2019-03-01 09:28:28 al 2019-07-02 15:52:26.
- Conformi ai conteggi di docs/WORKING_RULES.md §3.

### Archivio
- `data/_archive_20261003/frg_03-2019_07-2019/`: copia dei risultati attuali (2201 file, 197 MB), verificata con `sha256sum -c` (OK).
- `data/_archive_20261003/SHA256SUMS_inputs_inplace.txt`: checksum di `pred/`, `trig/`, modello `.h5` e cataloghi, lasciati in posizione.
- `benchmark/benchmark-crupi-2019.log` → `benchmark/_obsolete/benchmark-crupi-2019.log.txt` con nota "INVALIDO" in testa; il contenuto originale è intatto (SHA-256 `b373c972…` identico).

### Inventario dati (`python benchmark/audit/data_inventory.py` → `docs/DATA_INVENTORY.md`)
- Finestra 2019-03-01 → 2019-07-09: 131 giorni.
- Dati grezzi completi (12 NaI + 2 BGO + POSHIST): **122/131**. `bkg` 122/131, `pred/frg` 122/131.
- Mancano **2019-07-01 … 2019-07-09** (9 giorni, nessun file). Marzo–giugno completi a tutti i livelli.
- Due giorni hanno CSPEC `v01` (190308, 190411), una sola versione per giorno.
- I 4 eventi di riferimento dopo il 30 giugno (docs/WORKING_RULES.md §3) oggi non sono riproducibili.

### Stato degli input su disco (verifiche in sola lettura)
- `pred/frg_03-2019_07-2019.csv` e `pred/bkg_…`: 2 238 398 righe. **0 NaN** nelle colonne dei rate; **310 500 celle = 10.0 per canale** (= 1 035 buchi × 300 bin), identiche fra `frg` e `bkg`. Quindi **già sovrascritti** dallo step 4 (mtime 2026-10-01 09:34). Gli originali con NaN non esistono più. `frg` contiene anche la colonna `event` (da `add_trig_gbm_to_frg`).
- `bkg.met` e `bkg.timestamp` sono NaN nelle stesse 310 500 righe (comportamento del `predict` upstream, che azzera l'intera riga).
- La maschera su disco segue la regola upstream (indice dopo il buco, clip al primo e all'ultimo buco), non quella del `model_nn.py` attuale: 299/300 bin per buco, primo buco mascherato per metà.
- `met` in `frg`: 2 salti negativi e 4 valori duplicati ai confini fra giorni (2019-03-25/26, 2019-04-11/12): sovrapposizione fra file CSPEC consecutivi. Impatto minimo, da tenere presente.
- `trig/trig_…csv`: **0 NaN** su 2 238 398 righe → FOCuS non ha mai azzerato le curve ai bordi SAA nella produzione attuale (§5.3 confermato sui dati).

### Diff con upstream (`docs/DIFF_UPSTREAM.md`)
- Equivalenti: `trigs/focus.py`, `trigger.py`, `preprocess.py`.
- Regressioni **nuove** (non nella lista di docs/WORKING_RULES.md):
  1. `model_nn.predict` converte il MET in scala **TT** (`Time(…, format="fermi").datetime` senza `.utc`): timestamp **+69.184 s**. Verificato: MET 573284724.164 → 05:46:28.35 invece di 05:45:19.16. Non tocca i file attuali (prodotti con codice upstream-like), ma colpirebbe la prossima rigenerazione.
  2. `analyze.Segment` usa `iloc[start:end]` (fine esclusa) invece di `loc[start:end]`: **durate −4.096 s** ed eventi di un solo bin con durata 0.0 s. Verificato: evento 0 = 77.83 s (fork) contro 81.92 s (`triggers_table`, upstream).
  3. `analyze` ha perso l'offset FOCuS (`start_offset`) usato per la finestra delle sigma e per l'inizio dell'evento.
  4. `analyze` ha perso `check_against_gbmcatalogs` (statistica GRB detected/undetected/missing del paper).
  5. Configurazione di training cambiata rispetto a upstream/paper (scheduler LR rimosso, `beta_2`, `validation_split`, patience, seed) e `bs=8192` nella pipeline (upstream 2048).
  6. `model_nn.prepare` include il mese finale (`end31`); upstream lo esclude.
- Confermati sul codice: §5.1, §5.3, §5.6, §5.7.
- Punti **da decidere** (il nostro codice coincide con upstream, ma non con il testo del paper): FOCuS su rate (§5.4), maschera ±150 **bin** (≈ ±614 s) invece di ±150 s (§5.3), `t_max = 50` bin (204.8 s) invece di `dmax = 120.4 s`.

### §1: i due "sub-threshold GRB"
- 2019-03-08 22:10:12 → nel catalogo trigger GBM come **GRB190308923** (`bn190308923`, trigger 22:09:46.740, detector `n7 nb`); il nostro evento parte 25.4 s dopo.
- 2019-05-25 00:45:54 → **GRB190525032** (`bn190525032`, trigger 00:45:47.652); il nostro evento parte 6.5 s dopo e ha durata 0.0 s (effetto della regressione 2).
- Nessuno dei due è in `crupi_2019_known.csv`, `crupi_2019_unknown.csv` o `DeepGRB_catalog.csv`.
- In `events_table_loc.csv` attuale entrambi hanno `catalog_triggers` valorizzato. L'ipotesi "trigger time NaN nel join" non è ancora verificata: rimandata alla Fase 3.

### Non verificato in questa fase
- Il testo del paper (ho usato i parametri citati in docs/WORKING_RULES.md §2, non il PDF).
- Se la maschera delle celle 10.0 coincide con una ricostruzione esatta su tutti i 36 canali (controllati 3 canali: `n0_r1`, `n5_r0`, `nb_r2`).
- Il diff dei file non chiave rispetto a upstream (`localize_event.py`, `download_bkg.py`, `GBMutils.py`, `fermi_data_tools.py`), salvo quanto già noto dall'analisi della repo.
- Il funzionamento attuale del download FTP (non eseguito).

---

## 2026-10-03 — Fase 1: finestra dati

### Decisione (Giovanni, 2026-10-03)
- La baseline si ferma al **2019-06-30**: `END_DATE = "2019-06-30"` (non 2019-07-09 come in docs/WORKING_RULES.md §5.5).
- Conseguenza: i 4 eventi di riferimento di luglio (`2019_96`, `2019_97`, `2019_98`, `2019_99`) sono **fuori ambito** e vanno esclusi dal denominatore in Fase 3. docs/WORKING_RULES.md non è ancora stato aggiornato su questo punto.

### Modifiche (un commit per bug)
1. `7e41318`: `START_DATE`/`END_DATE` inclusivi in `connections/utils/config.py`; `utils/period.py` (`window_days`, `in_window`, `months_to_window`, `days_with_data`). Motivo: download e benchmark derivavano la finestra da etichette di mese con semantiche diverse (§5.5).
2. `04d7234`: download riscritto (§5.6). `download_days(start, end)` restituisce la colonna `day` (YYMMDD, con alias `id` per `build_table`); retry per giorno **e per file** (un rivelatore alla volta); i file vengono scaricati in staging, validati con i checksum FITS e poi spostati con `os.replace`; i file esistenti non vengono mai riscritti (gbm-data-tools apre i file in append: riscaricare un file esistente lo corromperebbe); verifica finale con log dei giorni incompleti. La pipeline non salta più download e preprocessing quando trova un CSV qualsiasi: preprocessa solo i giorni completi senza tabella.
3. `8175241`: benchmark con finestra esplicita; la verità a terra è limitata ai giorni con dati in `frg`, e quel numero di giorni è il denominatore del FAR.
4. Questo commit: `END_DATE` → 2019-06-30; lo script di inventario legge le date dalla config.

### Test (`python -m unittest discover -s tests -t .`)
- 19 test, tutti sulle funzioni reali (FTP sostituito da un fake che scrive FITS piccoli).
- Prima delle modifiche: 2/2 moduli in errore (`utils.period` e `download_days` assenti, nessuna colonna `day`). Dopo: **19/19 OK**.
- Coperti: inclusività della finestra, schedule con `day`, rilevamento dei file mancanti o vuoti, nessuna connessione se i dati sono completi, richiesta dei soli file mancanti, retry dopo un errore transitorio, file corrotto rifiutato e non spostato, file esistenti invariati (byte e mtime), wrapper legacy sui dati di produzione (122 giorni, senza FTP).

### Risultati misurati
- Inventario (`python -m benchmark.audit.data_inventory`): finestra 2019-03-01 → 2019-06-30, **122/122** giorni completi (CSPEC, POSHIST, `bkg`, `pred`).
- Idempotenza: `download_days()` con un `ftp_factory` che solleva un errore se chiamato → 122/122 completi, **nessuna richiesta FTP**. Con il `ContinuousFtp` reale: "All 122 days complete", nessun file scaricato.
- Finestra del benchmark (stessi helper della pipeline, sui dati attuali):
  - regola vecchia: 177 eventi del catalogo trigger GBM su 153 giorni;
  - regola nuova: **143 eventi su 122 giorni con dati** (GRB 93, TGF 27, UNCERT 11, LOCLPAR 7, SFLARE 5).

### Download reale interrotto (prova sul campo del nuovo downloader)
- Prima della decisione è partito il download di luglio da HEASARC. È stato fermato su richiesta.
- Installati e validati (checksum FITS OK): 2019-07-01 e 2019-07-02 completi (14 CSPEC + POSHIST ciascuno), più `glg_cspec_n0_190703_v00.pha`. Sono 29 file in totale; restano in `data/cspec` e `data/poshist`, fuori finestra e non letti da nessuno step (non esiste nessun `bkg/1907*.csv`).
- La cartella di staging `.download_190703_*`, con un `n1` interrotto a metà e mai validato, è stata rimossa.

### Note e limiti
- Importare `gbm.finder` apre già un socket FTP verso HEASARC (connessione a livello di classe nella libreria). "Idempotente" significa quindi: nessun file scaricato e nessuna richiesta per giorno, non zero connessioni.
- `test_pipeline.py` usa ancora un proprio download sulla sandbox: non toccato (fuori ambito della Fase 1).
- `ModelNN.prepare` usa ancora le etichette di mese (`end31`, M4 in DIFF_UPSTREAM): da allineare alle date in Fase 2.

---

## 2026-10-03 — Fase 2: correttezza del motore

### Decisioni (delegate, registrate in docs/WORKING_RULES.md §2)
Si segue il **codice upstream** dove differisce dal testo del paper: FOCuS sui rate, esclusione SAA ±150 bin, `t_max` = 50 bin. Verifiche a posteriori sui dati:
- **rate:** S nostro / S di Crupi sugli eventi abbinati ha mediana 1.02 (r0) e 1.03 (r1). Con i conteggi sarebbe ≈ 2.02 → Crupi usava i rate.
- **±150 bin:** troviamo **15** GRB del Burst Catalog senza dati, esattamente come il paper ("15 [...] due to the clipping"). Con ±150 s sarebbero circa 8 → la run di Crupi usava i 150 bin.
- **`t_max`:** nessuna evidenza nei dati; il paper dichiara dmax = 120.4 s. Effetto misurato come sensibilità (vedi sotto).

### Bug corretti (commit)
- `aa4a62d` analyze: sigma per evento (tableize) ripristinate; segmenti con fine inclusa (le durate erano più corte di un bin); offset FOCuS; C e tier CE (regola verificata su 99/99 righe di Crupi).
- `18740c5` model_nn: timestamp in **UTC** (erano TT, +69.184 s); bundle modello + scaler + metadati; ricetta di training upstream; seed; finestra di date; zeri a NaN in frg e bkg; nessuna sovrascrittura.
- `ad165d9` trigger: input in sola lettura; celle non valide passate a FOCuS come NaN (reset delle curve).
- `3674b9f` pipeline: cache versionata `data/runs/<start>_<end>/engine-v2/`; via la sanificazione `fillna(10)` e la riscrittura di frg; parametri stampati e salvati in `manifest.json`; batch NN 2048.
- `38bb236` **catalogo trigger** (regressione nuova, trovata durante la run): il file rigenerato il 2 ottobre aveva intervalli `trigger_time + timescale` (16 ms–4 s) invece di `time`→`end_time` (circa −135/+480 s, upstream). Con il file sbagliato il training escludeva 8 righe invece di 20 682. Rigenerato da HEASARC: sui 143 trigger del periodo gli intervalli coincidono con upstream (differenza massima 0.0).
- La prima run (con il catalogo sbagliato) è stata interrotta prima di qualunque predizione; bundle e manifest spostati in `data/_archive_20261003/aborted_engine_v2_run/`.

### Modello
- Riusato il modello del 2026-09-21, addestrato da codice equivalente a upstream (`477a950`) con gli iperparametri del paper (2048 unità, 64 epoche, batch 2048, lr 0.0008, dropout 0.02, split 52/23/25). **Nessun nuovo training.**
- Scaler ricostruito con lo stesso split deterministico (`random_state=0`). Confronto con le predizioni originali su 69 393 528 celle non sovrascritte: differenza relativa mediana 2.5e-5, massima 5.7e-3 → stesso scaler.
- Il modello originale di Crupi (2022) **non è disponibile** (nessun `.h5` nei branch upstream).

### Run `engine-v2` (commit motore `38bb236`, codice pulito)
- 2 238 398 bin; 310 800 righe mascherate (1036 buchi × 300; prima erano 310 500: upstream lasciava scoperti i lati esterni del primo e dell'ultimo buco); 0 celle a zero.
- FOCuS: picco 382.6σ; 3453 bin con r1 > 3σ su almeno un rivelatore.
- 179 trigger → **144 eventi** (R 105, S 18, P 21); durata mediana 72.5 s.
- `python -m benchmark.audit.engine_checks` → `results/engine_checks.md`: **SAA PASS** (nessun bin né confine di evento entro 150 s da un buco; il più vicino è a 622.6 s); **sigma PASS** (ricalcolo indipendente, differenza massima 2.3e-13).
- Test: 58/58 OK (`python -m unittest discover -s tests -t .`).

### Test
I test ora sono tutti sulle funzioni reali. Quelli di `models/tests/` sono stati rimossi perché testavano copie. Ogni bug corretto ha un test che fallisce sul codice precedente (verificato con `git stash`): analyze, model_nn, trigger, catalogo, classificatore.

---

## 2026-10-03 — Fase 3: validazione (`python -m benchmark.validate` → `benchmark/out/REPORT.md`)

### Regola di matching
Uno-a-uno (assegnazione greedy per distanza). Un riferimento è abbinato se il suo istante cade in [inizio evento − 2 bin, fine evento + 2 bin]; l'inizio evento è il change point FOCuS (`start_times_offset`). I riferimenti senza tempo restano nell'output come non abbinati. Sensibilità con margini di 10 s, 60 s e 1200 s.

### Risultati (run `engine-v2`, regola primaria)
- **Crupi noti: 70/71** (R 62/62, S 3/3, P 5/6). Mancante: `2019_7` (GRB190311600, P, n8): FOCuS r1 massimo 2.82σ entro ±60 s, sotto soglia.
- **Crupi inediti: 21/24** (R 12/13, S 3/3, P 6/8); R+S **15/16**. Mancanti:
  - `2019_0` (P): 2.45σ, sotto soglia;
  - `2019_58` (P): 2.97σ, sotto soglia;
  - `2019_81` (R): **rivelato ma unito**. Il nostro evento 122 (1154 s) copre `2019_80`, `2019_81` e `2019_82`, che Crupi elenca separati in 13 minuti; con il matching uno-a-uno l'evento va a `2019_80` (inediti) e a `2019_82` (noti).
- **Catalogo GBM** (143 trigger nei giorni con dati, 23 senza dati validi all'istante del trigger): rivelati 68/120. GRB del Burst Catalog: 93 nel periodo, **15 senza dati (paper: 15)**, rivelati **60/78** (paper 65/81 fino al 9/07); T90 > 4.096 s **54/65** (paper 60/68), T90 ≤ 4.096 s **6/13** (paper 5/13). TGF 0/23 e UNCERT 0/11: attesi con bin da 4 s.
- **S nostro / S di Crupi** (mediana): r0 1.02, r1 1.03, r2 0.76.
- Sensibilità: con 60 s GRB 63/78, con 1200 s 64/78; Crupi noti 70/71 con tutti i margini; inediti 22/24 solo a 1200 s.
- **Casi del §1:**
  - GRB190525032: abbinato (l'evento inizia 3.4 s prima del trigger).
  - GRB190308923: rivelato, ma il nostro evento inizia 25 s dopo il trigger. Fuori dal margine di 2 bin, abbinato con 60 s.
  - Nessuno dei due è nelle tabelle di Crupi. Non erano "scoperte".
  - L'ipotesi "trigger time NaN nel join" non è verificabile: il report che li presentava come scoperte era scritto a mano.

### Numero di eventi: 144 contro ~100 (criterio non raggiunto, diagnosi)
- 91 eventi abbinati a Crupi. 53 senza controparte né GBM né Crupi, di cui 1 (evento 7) dentro l'intervallo di catalogo di GRB190308923.
- Escluso:
  - **unità** (S ≈ quello di Crupi);
  - **clustering** (stesso codice upstream, merge 600 s);
  - **SAA** (nessun evento entro 150 s; distanza minima 672 s, mediana 5218 s);
  - **t_max**: con dmax = 120.4 s (29 bin) si ottengono 180 trigger → 144 eventi, stessi numeri di validazione;
  - **segmentazione**: solo 6/53 hanno un evento di Crupi entro 1 h.
- Contesto orbitale non anomalo (L mediano 1.12 contro 1.18 negli eventi abbinati).
- Il rivelatore `nb` compare in 45/53 di questi eventi contro 49/90 in quelli abbinati, ma i residui di `nb_r1` non sono distorti più degli altri canali (mediana +0.16%).
- **Causa più probabile:** la realizzazione della rete. La nostra rete ripete la ricetta di Crupi ma non è la sua (il modello originale non è disponibile), e i residui locali in alcune condizioni orbitali cambiano tra realizzazioni.
- Per confermarlo serve il test di stabilità su ≥ 2 seed (nuovi training): **non eseguito, richiede conferma**.

## 2026-10-03 — Fase 4: classificazione (`python -m benchmark.classify`)
- Leakage rimosso; `tests/test_classifier.py` verifica che le colonne del catalogo non cambino `predicted_class` (il test fallisce sul codice vecchio).
- Localizzazione: 144/144 eventi; deterministica (seriale = parallela, differenza 0.0).
- Su 91 eventi abbinati: **80/91 (87.9%)** con classe compatibile con quella tentativa di Crupi.
  - GRB: precision 0.91, recall 0.97.
  - SF: 5/5.
  - UNC(LP): recall 0.30 (5 classificati GRB).
  - TGF: 0/2.
- Limiti documentati: `fe_wet`/`fe_skw` costanti (la condizione `fe_wet > 2.054` della regola GRB è sempre vera); regola TGF irraggiungibile.

## 2026-10-03 — Fase 5: consegna
- `docs/BASELINE.md`: comandi, tempi misurati, formato della cache, come lanciare un altro periodo (`DEEPGRB_START_DATE`/`DEEPGRB_END_DATE`; training solo con `DEEPGRB_ALLOW_TRAINING=1`).
- Riproducibilità: rieseguendo `benchmark.validate` le tabelle CSV sono identiche byte per byte.
- Tag `baseline-2019-validated`: **non creato**. I criteri di recall sono raggiunti, quello sul numero di eventi no (diagnosticato sopra): la decisione spetta a Giovanni.

---

## 2026-10-03 — Fase 4, revisione: provenienza delle regole e baseline per XGBoost

### Provenienza (verificata sul codice upstream)
- Le regole sono la "manual classification logic" di `pipeline/script_classification2.py` (upstream, agosto–settembre 2023).
- Nello stesso script: decision tree uno-contro-resto di profondità 3, disegnati con `plot_tree` (le soglie con 2–3 decimali, come 0.392, 63.49, 2.054, 0.345, hanno la forma dei loro split); un blocco commentato si intitola "rule from Decision Tree"; molte varianti di soglie commentate (rifinitura manuale).
- Le random forest (multiclasse e uno-contro-tutti, 200 alberi, profondità 4, selezione L1 con LinearSVC, spiegazioni Anchor) servivano per l'importanza delle feature e come confronto, non come classificatore.
- Nessun output salvato collega ogni soglia a un albero specifico: "derivate da DT e rifinite a mano" è quanto si può affermare.
- Il capitolo 5.4 della tesi (arXiv:2401.15632) non era leggibile nella versione HTML.

### Correzioni
- Regola TGF ripristinata: `(non visibile) | (distanza dalla Terra < 80°)`. Il fork richiedeva durata < 0.2 s, irraggiungibile con bin da 4.096 s.
- Regola UNC(LP): ripristinata la condizione alternativa sull'incertezza di localizzazione. Crupi usava `max(ra_std, dec_std) > 100` sulla varianza, quindi qui la soglia è 10° sulla deviazione standard.
- Test `TestRulesMatchCrupi`: i flag coincidono con la trascrizione delle regole di Crupi (falliscono sul codice precedente).
- `benchmark/classify` salva un flag per regola (`rule_*`). Il report riporta le metriche uno-contro-resto, come nello script di Crupi.
- Classificazione precedente archiviata in `data/_archive_20261003/classification_before_rule_fix/`.

### Risultati (91 eventi abbinati, uno-contro-resto)
- GRB: precision 0.91, recall 0.97 (72/74).
- SF: 0.83 / 0.83.
- TGF: 0.33 / 0.33.
- UNC(LP): 0.53 / 0.80.
- GF: 0/2 (15 flag, tutti sbagliati).
- Etichetta singola compatibile con Crupi: 79/91.

### Per XGBoost (Fase 6 in docs/WORKING_RULES.md)
- Mancano ancora la regola FP e le feature `fe_*`. Sono calcolate con `tsfel` nel branch upstream `ric_review_28062023` (`models/localize_event.py`): curva di luce media dei rivelatori scattati, ±64 s, normalizzata min-max, wavelet con larghezze 1–9.
- `tsfel` e `xgboost` non sono installati nell'env.
- Etichette disponibili: 324 eventi di Crupi (2010-11: 73, 2014: 152, 2019: 99). Servono le run del motore anche su 2010-11 e 2014.

---

## 2026-10-04 — Riaddestramento della rete 2019: supporto nel codice (training non eseguito)

Richiesta: poter riaddestrare la rete 2019 da zero con il codice attuale, in run separate e senza toccare il modello legacy né la run `engine-v2`. Il training lo lancia Giovanni in background; qui **solo modifiche al codice e test** (nessun training reale eseguito).

### Commit
- `c15f18b` **import pigri di `gbm.finder`.** La libreria fa login FTP su HEASARC già all'import, e veniva importata da `connections/__init__` e `models/__init__`. Qualunque import della config richiedeva quindi la rete, anche con tutti i dati su disco: un nodo offline sarebbe fallito subito. Test: `tests/test_no_ftp_on_import.py` (fallisce con il codice precedente: `FINDER_LOADED`).
- `750e7e6` **report di training su stdout** con `flush=True`: parametri, seed, righe fit/validazione/test, una riga per epoca (loss, val_loss, lr, tempo), MAE per canale del miglior checkpoint, tempo totale. `metadata.json` del bundle aggiunge righe, epoche eseguite, epoca migliore, storia della loss, dispositivi, `training_seconds`, commit git, etichetta. La ricetta (iperparametri, scaler, split, callback di training) non cambia; `train()` rifiuta una cartella di bundle esistente. Test: `tests/test_training_report.py` (riga leggibile prima della fine del processo, con `python -u`).
- `ec01caa` **run etichettate e training forzato** (`utils/run_options.py`, `pipeline/pipeline_bkg.py`):
  - `DEEPGRB_RUN_LABEL=<etichetta>` → `data/runs/<start>_<end>/engine-v2-<etichetta>/` e bundle `data/nn_model/bundles/model_<start>_<end>_<etichetta>/`; se la cartella esiste, la pipeline si ferma prima di scrivere qualunque cosa.
  - `DEEPGRB_FORCE_TRAIN=1` → training anche sul periodo 2019; il modello legacy non viene mai caricato. Richiede `DEEPGRB_RUN_LABEL` e `DEEPGRB_TRAIN_SEED`.
  - `DEEPGRB_TRAIN_SEED=<intero>` → seed di python/numpy/TensorFlow, salvato nel metadata e nel manifest.
  - `DEEPGRB_REUSE_BUNDLE=1` → se il bundle etichettato esiste, lo usa invece di fermarsi.
  - `DEEPGRB_SKIP_DOWNLOAD=1` → salta gli step 1–2 dopo aver verificato che esistano tutte le tabelle giornaliere.
  - All'avvio stampa la GPU rilevata o l'avviso che il training girerebbe su CPU.
  - Senza queste variabili il comportamento è quello di prima (stessa cartella usata come cache, stesso modello legacy).
  - Test: `tests/test_run_options.py`. Il test chiave usa un modello legacy *corrotto* (bundle e `.h5`) e un vero `ModelNN` su dati di prova: con il flag di forzatura il training si completa e i file legacy restano identici (sha256), quindi non sono stati caricati.

### Verifiche eseguite
- Test: **72/72 OK** (`python -m unittest discover -s tests -t .`).
- Percorsi d'errore reali della pipeline (escono subito, senza training né cartelle nuove): `DEEPGRB_FORCE_TRAIN=1` senza etichetta, e senza seed.
- `data/runs/2019-03-01_2019-06-30/` contiene ancora solo `engine-v2` e `engine-v2-sens-tmax29`.

### Non verificato
- Nessun training reale sui dati 2019 (né su CPU né su GPU): tempi, memoria e convergenza non misurati.
- Su questo nodo TensorFlow non vede GPU. Il comportamento con una GPU (memory growth, velocità) non è stato provato.
- Riproducibilità bit a bit tra due training con lo stesso seed: su GPU TensorFlow non è deterministico per default (non attivato `TF_DETERMINISTIC_OPS`, per non cambiare la ricetta).

---

## 2026-10-04 — Domanda sul learning rate del training seed1 (solo documentazione)

Osservazione nel log `logs/train_seed1_clean.log`: i parametri dichiarano `lr=0.0008`, ma le righe di epoca mostrano `lr 1.00e-02` nelle epoche 1–4; la loss resta 109.5 / 106.1 / 105.3 nelle epoche 1–3 (val_loss 242.6 alla 3) e crolla a 12.1 alla 4.

### Da dove viene
- **Schedule di upstream**, non nostra. Introdotta da rcrupi nel commit `85542b5` (2023-01-14, "regulate learning rate with a scheduler piecewise") in `models/model_nn.py`:
  `scheduler(epoch)`: `lr*12.5` se `epoch < 4`, `lr*2` se `4 <= epoch < 12`, `lr/2` da `epoch >= 12`.
- Il nostro `_lr_schedule` in `models/model_nn.py` (commit `18740c5`) ne è la trascrizione identica, agganciata con `LearningRateScheduler`.
- Il valore base `lr = 0.0008` viene da `NN_PARAMS` in `pipeline/pipeline_bkg.py`, uguale alla chiamata upstream `nn.train(..., lr=0.0008, ...)` in `pipeline/pipeline_bkg.py` di upstream.
- Keras numera le epoche da 0, quindi:
  - epoche 1–4 del log → 0.0008 × 12.5 = **1.0e-2**;
  - epoche 5–12 → ×2 = **1.6e-3**;
  - dalla 13 → ×0.5 = **4.0e-4**.

  Coincide con il log (`1.60e-03` dall'epoca 5, `4.00e-04` dall'epoca 13).
- La riga `[train] parameters` stampa il lr **base** passato a `train()`; le righe di epoca stampano il lr **effettivo** dell'ottimizzatore. Il valore iniziale di Nadam viene sostituito dalla schedule già dalla prima epoca.

### Il plateau a loss ≈105 (`python -m benchmark.analysis.lr_check` → `benchmark/analysis/out/lr_check.json`)
Sullo stesso pool e split del training (1 164 300 righe di fit, 498 987 di validazione):
- MAE di un predittore sempre **zero**: 205.8 (fit), 205.9 (validazione); è anche il rate medio dei target;
- MAE della **mediana per canale**: 20.4 (fit e validazione).

Il plateau delle epoche 1–3 (≈105) non è quindi "rete con tutte le uscite a zero" (sarebbe ≈206), ma resta molto peggio del predittore banale per canale (≈20). È compatibile con una parte delle uscite ReLU spente durante la fase a lr alto, che si riattivano all'epoca 4. **Non verificato**: si salva solo il miglior checkpoint, non lo stato alle epoche 1–3.

Un indizio che upstream conoscesse questa fase: il codice di Crupi disegnava la curva di training a partire dalla quinta epoca (`plt.plot(history.history['loss'][4:])`).

### Collegato (trovato nell'analisi orbitale, `docs/ORBIT_ANALYSIS.md` §5)
- La rete seed1 prevede fondo 0 in 212 celle (6 bin interi): il log di training stampa `[ERROR] Predicted rate equal to 0 in 212 cells`. La rete legacy ne ha 0.
- `models/analyze.py::event_significance` non scarta B ≤ 0 (FOCuS sì), e due eventi seed1 (6 e 9, σ_C 881 e 39) sono artefatti di questo.
- Correzione possibile, **non applicata** (vincolo di sola lettura; cambierebbe gli eventi → `ENGINE_VERSION` 3).

Nessuna modifica all'addestramento.

## 2026-10-04 — Analisi orbitale degli eventi senza controparte

Vedi `docs/ORBIT_ANALYSIS.md`, generato da:
- `benchmark/analysis/orbit_analysis.py` (calcolo: CSV, PNG, `summary.json` in `benchmark/analysis/out/`, non versionati);
- `benchmark/analysis/orbit_report.py` (documento).

Sola lettura sul motore. Nota: `engine-v2/manifest.json` era già stato modificato da una pipeline lanciata senza `DEEPGRB_RUN_LABEL` (voce del 2026-10-04 07:41; pred/trig/results intatti).

---

## 2026-10-04 — Engine v3, flag SAA, correzioni al report

### Parte 1 — fondo previsto ≤ 0 (engine v3)
- `b11a317`: in `models/analyze.py::event_significance` un bin è valido solo se il fondo previsto è > 0 su tutti i canali, come in FOCuS. La stessa regola vale nella ricerca del picco di `localize_event`. Test: B = 0 e B < 0 (falliscono sul codice precedente).
- `3897f98`: `ENGINE_VERSION = 3` (cambia solo lo step 5).
  - Una run v3 riusa `pred/` e `trig/` della run v2 corrispondente: symlink dichiarati nel manifest (`reused_from`: run, bundle, commit d'origine); nessun modello caricato.
  - Il manifest registra `predicted_zero_cells`: celle e bin con fondo previsto ≤ 0.
  - Il training forzato non riusa mai.
- Run: `engine-v3` (da `engine-v2`, rete legacy) e `engine-v3-seed1` (da `engine-v2-seed1`), lanciate con `DEEPGRB_SKIP_DOWNLOAD=1` (più `DEEPGRB_RUN_LABEL=seed1` per la seconda).
- **Test (a)** (`tests/test_engine_v3_outputs.py`): con la rete legacy (0 celle a zero) `events_table.csv` e `triggers_table.csv` di v3 sono identici byte per byte a v2.
- **Test (c)** (`python -m benchmark.audit.compare_runs`, output in `benchmark/out/v3-seed1/compare_v2-seed1_v3-seed1.md`): 136 → 136 eventi, 136 coppie, **un solo evento cambia**:
  - **evento 6** (2019-03-07 01:51:23, 41 s, 12 rivelatori): S_r0/S_r1/S_r2/S_C da 880.9/764.9/99.2/880.9 a **29.1/25.7/14.3/29.1**; tempo, durata e rivelatori invariati.
  - **L'evento 9 non cambia (diversamente dall'atteso):** la sua finestra di S inizia un bin dopo i 3 bin a zero (2019-03-09 04:40:26–34). L'avevo segnalato in ORBIT_ANALYSIS con un margine di ±60 bin troppo largo; corretto in `3790913`.
  - Entrambi gli eventi sono attaccati a un tratto di 3 bin in cui la rete seed1 prevede 0 ed esistono solo con quella rete: probabili artefatti, non rimossi dal v3 (che corregge S, non i trigger).
- Validazione v3: nessun riferimento perso né guadagnato rispetto a v2 (insiemi abbinati identici per Crupi noti, inediti e GBM, per entrambe le reti).

### Parte 2 — flag SAA di post-processing (`0756c7c`, `models/saa_flags.py`)
Colonne aggiunte all'output della validazione (`events_flags.csv`); l'elenco degli eventi non cambia.

| run | abbinati flaggati | senza controparte flaggati | `saa_edge_short_passage` | `saa_region_proximity` |
|---|---|---|---|---|
| engine-v3 (legacy) | 1/91 | 38/53 | 24 (tutti senza controparte) | 39 |
| engine-v3-seed1 | 1/90 | 29/46 | 17 (tutti senza controparte) | 30 |

L'unico abbinato flaggato è l'evento 4 (2019-03-06 06:42), abbinato all'inedito di Crupi `2019_3`, che lui classifica UNC(LP): coerente con il flag.

### Parte 3 — correzioni
- `041f280` validate:
  - il seed del modello viene letto da `metadata.json` del bundle (quello della run d'origine se le predizioni sono riusate);
  - "Numero eventi ~100" diventa informativo, con i conteggi per rete (144 legacy, 136 seed1);
  - i limiti riportano la sovrapposizione tra reti (126 coppie, 18 solo legacy, 10 solo seed1), i passaggi SAA brevi non mascherati (45), il bordo nord della SAA e le celle a zero.
- `d1441e0` training: controllo di convergenza non bloccante.
  - Riferimenti calcolati sullo stesso split: MAE di un predittore costante (mediana per canale) e di uno sempre a zero, come in `lr_check.json`.
  - Salvato in `metadata.json` (`convergence`) e stampato nel log; avviso se il val_loss finale non scende sotto metà del riferimento costante.
  - L'addestramento non cambia.

### Risposta: learning rate del training (log seed1)
- **Da dove vengono 1e-2 (epoche 1–4), 1.6e-3 (5–12) e 4e-4 (da 13).** Dalla **schedule a gradini di upstream** (`LearningRateScheduler`), introdotta da rcrupi nel commit `85542b5` (2023-01-14):
  - `lr*12.5` se `epoch < 4`, `lr*2` se `4 <= epoch < 12`, `lr/2` dopo (epoche numerate da 0);
  - con lr base 0.0008 dà 1.0e-2, 1.6e-3 e 4.0e-4;
  - il nostro `_lr_schedule` ne è la trascrizione identica (`18740c5`);
  - **non** c'è nessun `ReduceLROnPlateau`, né in upstream né nel nostro codice (verificato con grep su entrambi): le riduzioni sono a epoche fisse, non dipendono dalla loss.
- **Perché i parametri dichiarano lr=0.0008.**
  - 0.0008 è il lr **base** passato a `train()`: `NN_PARAMS` della pipeline, uguale alla chiamata di upstream.
  - Nadam viene creato con quel valore, ma `LearningRateScheduler` imposta il lr all'inizio di ogni epoca, già dalla prima.
  - La riga `[train] parameters` stampa quindi il valore base; le righe di epoca il valore effettivo.
- **Perché le epoche 1–3 stanno a loss ≈105.** Riferimenti sullo stesso split (`benchmark/analysis/out/lr_check.json`):
  - predittore sempre zero: 205.9;
  - mediana costante per canale: 20.4.

  La loss di training a 109.5/106.1/105.3 è circa metà di quella "a zero", e alla terza epoca il **val_loss sale a 242.6, sopra il predittore a zero**: la rete non è solo ferma, è instabile. È la fase con lr 12.5 volte il valore base (1e-2) su Nadam, BatchNorm e uscite ReLU. Un meccanismo compatibile è che una parte delle uscite resti a zero e le altre oscillino.

  All'epoca 4, ancora a 1e-2, la loss scende a 12.1, e con 1.6e-3 si stabilizza (val 4.9 all'epoca 6). La scelta di upstream sembra deliberata: Crupi disegnava la curva di training a partire dalla quinta epoca (`history['loss'][4:]`). Il meccanismo esatto non è verificabile, perché si salva solo il miglior checkpoint.
- Nessuna modifica all'addestramento. Il nuovo controllo di convergenza guarda solo il risultato finale: su seed1 darebbe circa 4.4/20.4 ≈ 0.21 (OK).

## 2026-10-04 — Consolidamento del framework

Refactoring senza cambiamenti scientifici, da `e0e8da3` a `2465c0d` (dettaglio in `docs/REFACTOR_REPORT.md`):

- **Struttura**:
  - entry point unico `pipeline/pipeline_bkg.py` con blocco USER SETTINGS (le `DEEPGRB_*` hanno priorità);
  - tabella di stato e 9 step che si saltano da soli; localizzazione e classificazione (step 6), flag (step 7, `models/flags.py`), validazione (step 8, `<run>/validation/`) e resoconto (step 9, `<run>/RESULTS.md`, `docs/RUNS.md`) fanno ora parte della pipeline.
- **Configurazione e codice**:
  - configurazione unica in `connections/utils/config.py`, senza date;
  - logging unico (`utils/logs.py`, formato di Crupi);
  - legacy rimosso (`scripts/`, `paramtrig`, `GBMutils`, `load_data`, ...);
  - una sola conversione di tempo e una sola `md_table`;
  - commenti in inglese; CLI tutte con `--run`.
- **Manifest (difetto 17)**: parametri registrati una volta; modello descritto dal bundle (seed, sha256); una run incoerente si ferma.
- **Prova di invarianza** sul codice finale (`544a70d`), rigenerando engine-v3-seed1 ed engine-v3 dai pred/trig delle v2, senza training né FOCuS:
  - `events_table` `eb0207fb…` e `events_classified` `7924b0d6…` identici, come pure `triggers_table`, `events_table_loc`, `78f54718…` e `e9bab9e9…`;
  - identici tutti i CSV di validazione;
  - numeri: 136 (102/11/23), 70/71, 21/24, 67/120; legacy 144 (105/18/21), 70/71, 21/24, 68/120.
- **Repository**:
  - 161 → 103 file tracciati, 315.3 → 5.0 MB, nessun file > 5 MB;
  - 104 test verdi;
  - nessun dato cancellato: i 50 file tolti dal disco dal rebase locale sono stati ripristinati dagli oggetti git e verificati con i checksum d'archivio.
- **In attesa della conferma di Giovanni**: push di `main`, tag `v1.0-baseline`, eliminazione di `fix/baseline-2019` e `thesis` (comandi in REFACTOR_REPORT §8).

## 2026-10-05 — Resoconto automatico completo e run di verifica

- **`RESULTS.md` §6**, generata da `benchmark/report.py` e `benchmark/report_tables.py`:
  - matrice di confusione contro le classi **tentative** di Crupi, con conteggi, percentuali per riga (recall) e per colonna (precision), recall, precision e supporto per classe, accuracy;
  - matrice tipo di trigger GBM × classe predetta, con la concordanza di una mappatura **ipotetica** (GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP), UNCERT→UNC);
  - prima del join, ogni trigger abbinato viene verificato dentro la finestra dell'evento a cui punta: margine 8.192 s, change point non oltre `t_max` + 1 bin prima di `start_met`.
- **Nuova §9**: elenchi per nome di GRB, trigger non-GRB ed eventi di Crupi, con esito e classe predetta. Anche come CSV in `validation/`: `list_gbm_grb.csv`, `list_gbm_other.csv`, `list_crupi_events.csv`, `classification_metrics.csv`, `gbm_type_vs_class.csv`, `gbm_type_concordance.csv`.
- **Numeri** di engine-v3-seed1, identici in engine-v3-verify1:
  - 87 eventi con classe univoca, accuracy 75/87 (86.2%); riga GRB 68/0/0/1/1, GRB recall 97.1% e precision 90.7%;
  - concordanza GBM 62/67 (92.5%): GRB 57/59, SFLARE 4/5, LOCLPAR 1/3;
  - GRB del periodo: 59 rivelati, 19 mancati, 15 senza dati;
  - eventi di Crupi: 91 ritrovati, 4 no;
  - legacy (engine-v3): concordanza 63/68.
- **Run di verifica** `engine-v3-verify1`, fatta con `pipeline/pipeline_start.py`: bundle seed1 copiato, step 3–9 eseguiti da zero. `pred/bkg.csv`, `trig/trig.csv`, tutti i file di `results/` e i CSV di validazione sono identici byte per byte a quelli di engine-v3-seed1.
- Solo lo step 9 è stato rigenerato sulle run esistenti. I checksum di `docs/BASELINE_2019.md` §6 sono invariati. 11 nuovi test, 115 in tutto, verdi.
