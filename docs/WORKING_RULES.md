# DeepGRB — Riproduzione rigorosa dei risultati di Crupi (2019) e baseline affidabile

> Documento operativo: regole di lavoro del progetto. Leggilo tutto prima di toccare il codice.
> Autore: Giovanni Pio Martello (Poliba, tesi su DeepGRB, cluster ReCaS). Scrivi in italiano con me; codice, commit e nomi di variabili in inglese.

## 0. Obiettivo

Far sì che `pipeline/pipeline_bkg.py` **riproduca, in modo verificabile e privo di errori logici**, i risultati del paper di Crupi et al. (Exp. Astron. 56:421, 2023; tesi arXiv:2401.15632) sul periodo **1 marzo – 9 luglio 2019**:

1. gli eventi **noti**, cioè presenti nel catalogo trigger ufficiale Fermi-GBM (74 righe nella Tabella 11 del paper);
2. gli eventi **inediti**, cioè non presenti nel catalogo GBM (25 righe nella Tabella 10 del paper).

Questa sarà la **base fidata** da cui partire per i dati 2024 (picco Ciclo Solare 25). Per ora **non** si lavora su XGBoost né sul 2024.

**Definizione di "fatto":** un solo comando rigenera da zero, in modo deterministico, `benchmark/out/REPORT.md` con tutte le metriche calcolate dal codice (nessun numero scritto a mano), e i criteri di accettazione della §6 sono soddisfatti oppure ogni scostamento è diagnosticato evento per evento.

## 1. Stato attuale: cosa NON fidarti

I risultati attuali sono **sbagliati** e vanno considerati invalidi. In particolare **non riutilizzare** `benchmark/benchmark-crupi-2019.log` né le sue cifre: 144 candidati, T=99, Recall 93.94%, FAR 0.35, 77 "sub-threshold", classe SF/GRB. Il file è scritto a mano e non corrisponde a un'esecuzione del codice (l'esecuzione reale dà T=177 e altre distribuzioni di classe).

L'introduzione di `deltaT = 1200 s` ha fatto apparire due "sub-threshold GRB" (2019-03-08 22:10:12 e 2019-05-25 00:45:54) che risultavano però già esistenti. Ipotesi da verificare, non da assumere: il join con il catalogo trigger perde il trigger time (NaN), per cui eventi con controparte reale vengono trattati come inediti. Controlla se i due eventi sono nel catalogo GBM (il nome GBM `bnYYMMDDfff` usa la frazione di giorno: 22:10:12 corrisponde a circa 0.924, quindi prova `bn190308924`) e se corrispondono a righe del CSV di riferimento di Crupi. Dalle tabelle del paper risulta che non sono tra i 25 inediti di Crupi.

## 2. Contesto tecnico (sintesi)

Pipeline (cache a ogni step: se l'output esiste lo step viene saltato):

1. download CSPEC + POSHIST (`models/download_bkg.py`)
2. preprocess → `data/bkg/YYMMDD.csv` (`models/preprocess.py`): 36 rate (12 NaI × 3 bande r0 28–50, r1 50–300, r2 300–500 keV) + feature orbitali, bin 4.096 s
3. rete neurale (`models/model_nn.py`): FFNN 60→2048→2048→1024→36, loss MAE, Nadam, 64 epoche, batch 2048; output `pred/frg_*.csv` (osservato) e `pred/bkg_*.csv` (fondo)
4. Poisson-FOCuS (`models/trigger.py`, `models/trigs/focus.py`)
5. clustering (`models/analyze.py`): soglia 3σ in r1 su ≥1 rivelatore, merge segmenti entro 600 s
6. classificazione (`models/event_classifier.py`, `CrupiEventClassifier`)
7. localizzazione PSO + benchmark (`models/localize_event.py`, `benchmark/validate_results.py`)

Parametri del paper da rispettare (verifica che il codice li usi davvero): soglia T = 3σ in r1 su almeno 1 rivelatore; `dmax` = 120.4 s, `mu_min` = 1.2; clustering < 600 s; esclusione di ±150 s attorno a ogni passaggio in SAA di durata ≥ 500 s; bin 4.096 s; training senza SAA e senza intervalli dei trigger GBM; una rete per periodo; significatività evento S = (N−B)/√B con N e B integrati sull'intervallo dell'evento e sui rivelatori scattati, e solo sui conteggi sopra una soglia basata su quantile (nota 2 del paper); consistency C = max(S_r0, S_r1, S_r2).

Il repo upstream è `github.com/rcrupi/DeepGRB`. Usalo come riferimento: aggiungilo come remote `upstream` e fai il diff dei file chiave (`models/trigger.py`, `models/analyze.py`, `models/trigs/focus.py`, `models/model_nn.py`, `models/preprocess.py`) rispetto al nostro fork. Ogni differenza deve essere classificata come **intenzionale** (porting Keras 3 / Pandas 2 / HPC) oppure **regressione**.

## 3. Verità di riferimento (ground truth)

File da mettere in `benchmark/reference/` (te li fornisco, estratti dal paper):

- `crupi_2019_known.csv`: 74 eventi con controparte nel catalogo GBM (64 R, 4 S, 6 P)
- `crupi_2019_unknown.csv`: 25 eventi inediti (13 R, 3 S, 9 P)

Colonne: `n,id,starred,trigger_time_utc,duration_s,detectors,catalog_name,S_r0,S_r1,S_r2,CE`. Il tier **CE** è definito dal paper: **R** (robust) se scattano più rivelatori e più bande, **S** (solid) se più rivelatori ma una sola banda, **P** (probable) in tutti gli altri casi. Le sigma `>10` sono salvate come stringa `>10`.

Attenzione a tre punti:

- **Finestra temporale:** il paper copre 2019-03-01 → 2019-07-09. 4 eventi di riferimento cadono dopo il 30 giugno (`2019_96` del 2019-07-02, `2019_97`, `2019_98`, `2019_99` del 7–8 luglio). La nostra pipeline oggi si ferma al 30 giugno: quei 4 eventi sono **irriproducibili** finché i dati non coprono il 9 luglio.
- **Conteggio:** le tabelle contengono 99 righe (74+25); il testo del paper dice 100 eventi (uno è un artefatto non in tabella).
- **Due verità diverse, da non mescolare:**
  - **A. Catalogo ufficiale GBM** (`data/gbm_trig_catalog.csv`, `gbm_burst_catalog.db`): tutti i tipi di trigger (GRB, SFLARE, TGF, LOCLPAR…) nella finestra. Misura quanto troviamo di ciò che Fermi ha già visto.
  - **B. Tabelle di Crupi** (i due CSV sopra): misura la **riproduzione** del paper, inediti inclusi.

Numeri del paper (2019) da riprodurre come ordine di grandezza: catalogo Burst GBM 96 GRB, di cui 15 senza dati per il clipping SAA; sui rimanenti 81 ne vengono rivelati 65; con T90 > 4.096 s: 60/68 (88%); con T90 < 4.096 s: 5/13 (34%); totale eventi 100 (74 noti, 25 incerti, 1 falso).

## 4. Regole di lavoro (obbligatorie)

1. **Lavora su un branch** (`fix/baseline-2019`), commit piccoli e atomici, un commit per bug. Messaggi in inglese.
2. **Nessun numero scritto a mano.** Ogni cifra in un report deve essere stampata da uno script che legge file su disco. Il vecchio `benchmark-crupi-2019.log` va archiviato in `benchmark/_obsolete/` con una nota in testa "INVALIDO".
3. **Non tarare i parametri per far tornare i numeri.** I parametri sono quelli del paper (§2). Se un risultato non torna, diagnostica l'evento e spiega la causa; non cambiare soglie.
4. **Non toccare rete neurale e FOCuS** se non un test dimostra un bug. L'analisi della repo li giudica solidi (MAE train/test allineate; FOCuS coerente col paper), ma verifica le unità di ingresso a FOCuS (§5.4).
5. **Non cancellare dati** (~35 GB in `data/`). Per invalidare cache sposta in `data/_archive_YYYYMMDD/`. Chiedimi conferma prima di qualunque operazione distruttiva o di un nuovo training lungo su GPU.
6. **Non sovrascrivere mai gli input** (`pred/frg_*`, `pred/bkg_*`): i risultati derivati vanno in file separati.
7. **Test su funzioni reali**, non su copie locali (oggi `models/tests/` testa copie). Ogni bug corretto ha un test che fallisce prima e passa dopo.
8. **Tieni `docs/WORKLOG.md`**: per ogni passo scrivi cosa hai cambiato, perché, e il risultato misurato (con valori reali).
9. Se qualcosa è ambiguo, o la correzione cambia in modo sostanziale il significato scientifico, **fermati e chiedimi**. Non indovinare.
10. A fine di ogni fase mandami un riepilogo breve: cosa è cambiato, numeri misurati, file prodotti, dubbi aperti.

## 5. Bug noti da correggere (in ordine di impatto)

Sono emersi da un'analisi della repo e da me. **Verifica ciascuno nel codice prima di intervenire**, poi correggi.

### 5.1 Significatività σ attribuite agli eventi sbagliati
Il refactor ha rimosso da `analyze.py` il calcolo delle sigma per evento (vecchia `tableize`). `enrich_events_with_catalog` ora legge `sigma_r0/r1/r2` da `triggers_table.csv` (177 trigger, *prima* del merge) e le unisce su `trig_ids`; gli ID dei 144 eventi dopo il merge non coincidono: circa 140 eventi su 144 ricevono sigma di un altro trigger. Tutte le regole di classificazione dipendono da queste sigma.
**Fix:** ripristina il calcolo per evento dalla git history (`git show 0cd56c2^:models/analyze.py`), integrando N e B sull'intervallo dell'evento come da paper (§2), e calcola C = max(S_r0,S_r1,S_r2) e il tier CE (R/S/P). Test: per ogni evento, S_r1 ricalcolato a mano da `frg`/`bkg` coincide con la colonna.

### 5.2 Il classificatore legge la risposta dal catalogo (data leakage)
Se `catalog_triggers` contiene "GRB" o "TGF", `resolve_label` restituisce quella classe, e lo step 6 riempie proprio quel campo dal catalogo GBM. La matrice di confusione sugli eventi abbinati è gonfiata per costruzione.
**Fix:** `predicted_class` dipende solo da feature fisiche (sigma, HR, distanza da Sole/Terra, SAA/poli, durata, numero rivelatori). Le colonne del catalogo (`catalog_name`, `catalog_class`, `catalog_match`) stanno su campi separati e si usano solo in valutazione. Inoltre: `fe_wet`/`fe_skw` non vengono mai calcolate e restano costanti (la condizione `fe_wet > 2.054` è sempre vera); la regola TGF (`duration < 0.2 s`) non può scattare con bin da 4.096 s. Documenta questi limiti nel report, non "aggiustarli" in silenzio.

### 5.3 Step 4 distrugge il mascheramento SAA e sovrascrive i dati
`fillna(10.0)` rimpiazza i NaN messi apposta attorno alla SAA e risalva `frg`/`bkg` sopra gli originali; FOCuS non azzera più le curve ai bordi SAA e lo `zero_mask` di `run_trigger` non fa niente.
**Fix:** niente `fillna`, i NaN devono arrivare a FOCuS (che li usa per resettare); nessuna scrittura sopra i file di ingresso. Il filtro è ±150 bin attorno ai buchi > 500 s; verifica che l'unità sia coerente con il paper (±150 **secondi**; a 4.096 s/bin sono circa ±37 bin) e che i 150 bin del codice non siano un errore di unità. Test: nessun trigger nei ±150 s attorno a un buco SAA > 500 s.

### 5.4 Unità di ingresso a FOCuS (rate vs conteggi)
FOCuS riceve *rate* (conteggi/s) invece di conteggi per bin. Con statistica di Poisson questo cambia la scala delle σ (di un fattore √4.096). Confronta con `upstream` (`models/trigger.py`): se l'originale passa conteggi per bin, allinea; se passa rate, documenta. Se cambia, l'effetto sulle σ e sul numero di trigger va misurato e riportato.

### 5.5 Finestra temporale e denominatore del FAR
`END_MONTH="07-2019"` è un limite esclusivo per il download (dati fino al 30 giugno) ma il benchmark aggiunge un mese e usa 153 giorni con 177 eventi di verità, includendo luglio senza dati. Gonfia i FN e sgonfia il FAR.
**Fix:** definisci date esplicite inclusive (`START_DATE=2019-03-01`, `END_DATE=2019-07-09`) in `connections/utils/config.py`, usate sia da download che da benchmark. Il FAR si calcola su giorni con dati validi realmente presenti.

### 5.6 Download da zero rotto
`download_spec` restituisce `id/tStart` ma la pipeline cerca la colonna `day`; senza di essa usa l'indice 0..N e i controlli di retry fanno glob su `*0*`.
**Fix:** colonna `day` esplicita (formato `YYMMDD`); retry per giorno e per file; verifica finale che per ogni giorno della finestra esistano CSPEC (12 NaI) e POSHIST; log dei giorni mancanti.

### 5.7 Modello salvato non ricaricabile, scaler non persistito
`train(bool_train=False)` cerca `model_03-2019_07-2019.keras` ma su disco c'è `model_..._4.4_2026-09-21.h5`; lo scaler viene ricalcolato sui dati correnti.
**Fix:** salva modello e `StandardScaler` insieme (joblib) con metadati (periodo, seed, versioni, MAE); carica sempre entrambi. Fissa i seed (numpy, TF, python) e registrali.

### 5.8 Problemi minori
- `ra_std`/`dec_std` in localize contengono la varianza, non la deviazione standard.
- `MAX_DET_NUMBER=13` non scarta mai niente (i NaI sono 12).
- `benchmark/validate_results.py` ha `base_dir` su `benchmark/data/...` (non esiste); tolleranza 10 s.
- `scripts/.../plot_hist_residual.py` e `download_event_grb.py` usano `Optional` senza import.
- `manual_label.py`: etichette posizionali (100 per il 2019) che non corrispondono più agli eventi; sostituiscile con le etichette dai CSV di riferimento, agganciate per tempo.
- `test_pipeline.py` stampa "ALL PIPELINE MODULES OPERATIONAL" anche con precision 0.06 e FAR 8/giorno (la rete da 10 epoche su 7 giorni sottostima il fondo e i 69 "eventi" sono orbite intere). Aggiungi asserzioni di qualità, oppure rinomina il test in smoke test e dichiara che non valida la scienza.

## 6. Fasi di lavoro e criteri di accettazione

### Fase 0 — Audit e congelamento (nessuna modifica al codice)
- Crea il branch; esegui i test esistenti; archivia gli output attuali (`results/frg_03-2019_07-2019/`) con checksum in `data/_archive_YYYYMMDD/`.
- Aggiungi il remote `upstream` e produci `docs/DIFF_UPSTREAM.md` con la classificazione (intenzionale / regressione) di ogni differenza nei file chiave.
- Inventario copertura dati: tabella giorno × (CSPEC, POSHIST) da 2019-03-01 a 2019-07-09.
- **Accettazione:** WORKLOG avviato, DIFF_UPSTREAM e inventario scritti, nulla di funzionale cambiato.

### Fase 1 — Finestra dati
- Implementa §5.5 e §5.6; scarica i giorni mancanti (1–9 luglio 2019 e qualunque buco).
- **Accettazione:** l'inventario mostra copertura completa fino al 9 luglio; il download è idempotente (una seconda esecuzione non scarica nulla).

### Fase 2 — Correttezza del motore
- Implementa §5.1, §5.3, §5.4, §5.7 (il training/riaddestramento richiede la mia conferma), con i test della regola 7.
- Rigenera step 3–5 usando una cache nuova con chiave `(periodo, versione_codice)`; non riusare la cache vecchia.
- **Accettazione:** test verdi; `events_table.csv` ha sigma coerenti per evento; nessun trigger nei ±150 s attorno ai buchi SAA; parametri del paper verificati e stampati nel log all'avvio.

### Fase 3 — Matching e validazione (nuovo `benchmark/validate.py`, deterministico)
Matching **uno-a-uno** (un evento ↔ al massimo un riferimento e viceversa), mai molti-a-molti, e senza scartare righe con tempo NaN: un evento senza controparte ha `matched=False`, non sparisce.

- **Regola di match primaria:** l'istante del trigger di riferimento cade in `[t_start − 2·4.096 s, t_end + 2·4.096 s]` dell'evento; in caso di più candidati vince il più vicino. 1200 s **non** è la regola primaria: è troppo larga rispetto a eventi di 4–100 s e produce falsi abbinamenti; riportala solo come analisi di sensibilità, insieme a 10 s e 60 s.
- **Validazione A (catalogo GBM):** eventi del catalogo trigger nella finestra e con dati utili (esclusi quelli entro ±150 s da un buco SAA > 500 s, che il paper conta come "missing"). Riporta TP/FN per tipo (GRB, SFLARE, TGF, LOCLPAR…), e per i GRB del Burst Catalog la recall con T90 > 4.096 s e < 4.096 s.
- **Validazione B (Crupi):** match con `crupi_2019_known.csv` e `crupi_2019_unknown.csv` **separatamente**; per ogni lato elenca i non abbinati con S_r1 e tier CE.
- **Eventi nostri senza controparte** (né GBM né Crupi): tabella dedicata, mai chiamati "scoperte". Per i due casi del §1 spiega esplicitamente la causa.
- **Stabilità:** riporta quanto varia l'insieme degli eventi tra almeno 2 seed del training (se la mia conferma permette il riaddestramento); gli eventi P (singolo rivelatore, singola banda, S_r1 ≈ 3–5) sono i più sensibili.
- **Accettazione (obiettivi, non soglie da forzare):**
  - ≥ 90% degli eventi noti di Crupi (≥ 67/74) ritrovati; tutti gli R e S noti ritrovati salvo diagnosi motivata;
  - ≥ 90% degli inediti R+S (≥ 15/16) ritrovati;
  - ≥ 70% degli inediti complessivi (≥ 18/25) ritrovati, con i P mancanti spiegati;
  - recall GRB con T90 > 4.096 s dell'ordine dell'88% e con T90 < 4.096 s dell'ordine del 34%;
  - numero totale di eventi nostri dell'ordine di 100 ± qualche decina; se è molto più alto (per esempio 144, o circa 177) indaga clustering e unità prima di andare avanti.
  Se non sono raggiunti: **diagnosi per evento** (fondo stimato, σ, SAA, clustering), non ritocco dei parametri.

### Fase 4 — Classificazione (solo baseline onesta)
- Con σ corrette e senza leakage, valuta `CrupiEventClassifier` contro le classi tentative dei CSV di Crupi (SF, GRB, GF, TGF, UNC(LP)), agganciate per tempo. Confusion matrix, precision/recall per classe, calcolate dal codice.
- **Fuori ambito ora:** XGBoost, 2024, riaddestramento del classificatore.
- **Accettazione:** matrice senza leakage (verifica con un test che azzera il catalogo e controlla che `predicted_class` non cambi).

### Fase 5 — Report e consegna
- `python -m benchmark.validate` genera `benchmark/out/REPORT.md` (+ CSV delle tabelle) con tutte le metriche; stampa versioni, seed, periodo, hash del commit.
- `docs/BASELINE.md`: comandi esatti per riprodurre tutto, tempi, risorse ReCaS (4 vCPU/16 GB; GPU H100 MIG per il training), formato della cache, e come lanciare un altro periodo (2024) senza collisioni di cache: ogni periodo ha la sua directory di output.
- Tag git `baseline-2019-validated` quando la Fase 3 è accettata.
- **Accettazione:** una persona nuova esegue i comandi di BASELINE.md e ottiene gli stessi numeri.

## 7. Cosa mi aspetto da te in ogni risposta

1. Prima di ogni modifica: una riga su cosa farai e perché.
2. Dopo: il risultato misurato (numeri reali dai file), non "dovrebbe funzionare".
3. Se un numero ti sembra troppo bello (per esempio recall 100%, o precision 100% su una classe), cerca la causa prima di riferirlo: quasi sempre è leakage o un match troppo permissivo.
4. Elenca sempre cosa **non** hai verificato.
