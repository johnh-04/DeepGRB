# WORKLOG — baseline 2019

Ogni voce: cosa è cambiato, perché, risultato misurato (valori reali dai file).

---

## 2026-10-03 — Fase 0: audit e congelamento (nessuna modifica funzionale)

### Ambiente
- Branch `fix/baseline-2019` creato da `thesis` @ `2bf1003`.
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
