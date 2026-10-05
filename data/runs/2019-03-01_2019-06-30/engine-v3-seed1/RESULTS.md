# Resoconto della run `engine-v3-seed1` (2019-03-01 → 2019-06-30)

Generato da `benchmark/report.py` (step 9 di `pipeline/pipeline_bkg.py`); validazione del 2026-10-04 16:57 UTC, commit `21e4db1703`. Tutti i numeri sono letti da file della run; le tabelle complete sono in `validation/` e `results/`.

## 1. Run, rete e parametri

- Periodo: **2019-03-01 → 2019-06-30** (giorni UTC inclusi); run `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`.
- Motore: engine v3; esecuzioni: 2026-10-04 16:51 commit `21e4db1703` (step da eseguire all'avvio: 3, 4, 5, 6, 7, 8, 9); 2026-10-04 17:03 commit `21e4db1703` (step da eseguire all'avvio: 9).
- Rete: bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1`; seed di training 1; checksum sha256 del bundle `0eae86f65d97b285976955b98d80a8b5df8202fb8ea9df84973958eb7bc9ee08`.
- Predizioni (step 3) e trigger (step 4) riusati da `data/runs/2019-03-01_2019-06-30/engine-v2-seed1` (engine v2, symlink).
- Addestramento: 64 epoche (migliore 57), 2048 unità, lr 0.0008, batch 2048, 378.0 s su /physical_device:GPU:0.
- Parametri: bin 4.096 s; FOCuS mu_min 1.2, t_max 50 bin (ingresso: rates (counts/s)); soglia 3.0 σ in r1 su ≥ 1 rivelatori; merge 600 s; maschera SAA ±150 bin attorno ai buchi > 500.0 s.

## 2. Eventi

- Totale: **136**; tier CE: R 102, S 11, P 23 (R: più rivelatori e più bande; S: più rivelatori, una banda; P: gli altri).
- Abbinati al catalogo trigger GBM: 67; a Crupi noti: 70; a Crupi inediti: 21. Senza controparte: **46** (0.38 al giorno su 122 giorni con dati).

## 3. Catalogo ufficiale Fermi-GBM

Regola primaria: abbinamento uno-a-uno, istante del trigger entro [inizio evento − 8.192 s, fine evento + 8.192 s].

- Trigger nel periodo, nei giorni con dati: 143; senza dati validi all'istante (maschera SAA/buchi): 23; disponibili: 120; rivelati: **67**.
- Entro ±150 s da un buco > 500 s: 8 trigger.

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 59 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

GRB del Burst Catalog (T90):

|  | questa run | paper (fino al 9/07/2019) |
|---|---|---|
| GRB nel periodo | 93 | 96 |
| senza dati (SAA) | 15 | 15 |
| rivelati / disponibili | 59/78 (75.6%) | 65/81 |
| T90 > 4.096 s | 54/65 (83.1%) | 60/68 (88%) |
| T90 ≤ 4.096 s | 5/13 (38.5%) | 5/13 (34%) |

Sensibilità alla regola di abbinamento:

| margine | GBM rivelati/disponibili | GRB | Crupi noti | Crupi inediti |
|---|---|---|---|---|
| primary (2 bins) | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 10 s | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 60 s | 69/120 | 61/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 1200 s | 72/120 | 63/78 | 70/71 (98.6%) | 21/24 (87.5%) |

## 4. Confronto con Crupi et al. (2023)

| criterio (docs/WORKING_RULES.md §6) | misurato | esito |
|---|---|---|
| Noti di Crupi ritrovati ≥ 90% | 70/71 (98.6%) | ✔ |
| Tutti gli R e S noti ritrovati | 65/65 (100.0%) | ✔ |
| Inediti R+S ritrovati ≥ 90% | 15/16 (93.8%) | ✔ |
| Inediti complessivi ≥ 70% | 21/24 (87.5%) | ✔ |
| Recall GRB T90 > 4.096 s ~ 88% (paper) | 54/65 (83.1%) | ordine di grandezza |
| Recall GRB T90 ≤ 4.096 s ~ 34% (paper) | 5/13 (38.5%) | ordine di grandezza |
| Numero eventi ~ 100 (paper, fino al 9 luglio) | 136 | informativo: dipende dalla rete |

- Noti (Tabella 11; in finestra 71 di 74): ritrovati **70/71 (98.6%)**; per tier: R 62/62, S 3/3, P 5/6.
- Inediti (Tabella 10; in finestra 24 di 25): ritrovati **21/24 (87.5%)**; per tier: R 12/13, S 3/3, P 6/8.

Noti non ritrovati:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_7 | 2019-03-11 14:23:37 | n8 | GRB190311600 | 3.36 | P | True | 2.96 | 47299.20 | below threshold: max FOCuS r1 within ±60 s = 2.96 sigma |

Inediti non ritrovati:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_0 | 2019-03-01 09:28:28 | n6 | UNKNOWN: UNC(LP) | 3.63 | P | True | 1.65 | -10968.94 | below threshold: max FOCuS r1 within ±60 s = 1.65 sigma |
| 2019_58 | 2019-05-14 07:38:41 | na | UNKNOWN: TGF | 3.09 | P | True | 2.87 | 10307.34 | below threshold: max FOCuS r1 within ±60 s = 2.87 sigma |
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 10.09 | -228.48 | detected but merged: inside our event 115, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

Significatività, nostro S rispetto a quello di Crupi (eventi abbinati con S di riferimento numerico):

| banda | eventi | mediana S_nostro/S_Crupi | 16° pct | 84° pct |
|---|---|---|---|---|
| r0 | 30 | 1.00 | 0.92 | 1.07 |
| r1 | 33 | 1.01 | 0.90 | 1.06 |
| r2 | 10 | 0.74 | 0.64 | 1.10 |

Casi del §1 di docs/WORKING_RULES.md (i due "sub-threshold GRB" del vecchio log):

| tempo (§1) | trigger GBM | trigger_time | rivelato (regola primaria) | evento | inizio evento - trigger [s] | eventi nostri entro ±60 s | in tabelle Crupi |
|---|---|---|---|---|---|---|---|
| 2019-03-08 22:10:12 | GRB190308923 | 2019-03-08 22:09:46.740 | False |  |  | 0 | False |
| 2019-05-25 00:45:54 | GRB190525032 | 2019-05-25 00:45:47.652 | False |  |  | 0 | False |

## 5. Eventi senza controparte e flag di post-processing

Gli eventi senza controparte (né catalogo GBM né tabelle di Crupi) **non sono scoperte**: sono candidati da verificare. I flag aggiungono colonne e non cambiano l'elenco degli eventi (definizioni in `models/flags.py` e `docs/ORBIT_ANALYSIS.md`): `saa_edge_short_passage` (inizio entro 200 s da un passaggio SAA il cui buco non è mascherato), `saa_region_proximity` (Fermi entro 3.5° dalla regione SAA), `near_zero_prediction` (evento ±5 bin che tocca un bin con fondo previsto ≤ 0).

| eventi | n | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | almeno uno |
|---|---|---|---|---|---|
| abbinati Crupi/GBM | 90 | 0 | 1 | 0 | 1 |
| senza controparte | 46 | 17 | 29 | 2 | 31 |
| tutti | 136 | 17 | 30 | 2 | 32 |

Eventi senza controparte (46) per combinazione di flag:

| flag | eventi |
|---|---|
| saa_edge_short_passage, saa_region_proximity | 17 |
| nessuno | 15 |
| saa_region_proximity | 12 |
| near_zero_prediction | 2 |

Tier: R 29, S 5, P 12; distanza dal buco SAA più vicino: minima 680 s, mediana 5212 s. Elenco completo: `validation/events_without_counterpart.csv`.

## 6. Classificazione (baseline euristica di Crupi)

Regole della "manual classification logic" di Crupi (`pipeline/script_classification2.py` upstream): soglie lette da decision tree uno-contro-resto e rifinite a mano. Baseline volutamente semplice, da superare con XGBoost (fase 6). Mancano la regola FP e le feature `fe_*` (tsfel). Il classificatore non legge le colonne del catalogo (`tests/test_classifier.py`). Fuori dai GRB è debole.

Classi predette su tutti gli eventi: GRB 101, UNC(LP) 17, TGF 7, UNC 5, SF 5, GF 1.

### 6.1 Classe predetta contro le classi tentative di Crupi

Le classi di Crupi sono **tentative** (assegnate a mano nel paper, a volte multiple come `GRB/GF`): misurano la coerenza con il suo giudizio, non la natura fisica degli eventi.

Su 91 eventi abbinati a Crupi, classe predetta tra quelle tentative (anche multiple): 79/91 (86.8%).

Matrice di confusione sugli eventi con classe Crupi univoca: **87** eventi; accuracy complessiva **75/87 (86.2%)**. Righe: classe di Crupi; colonne: classe predetta.

Conteggi:

| Crupi | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 68 | 0 | 0 | 1 | 1 |
| SF | 0 | 4 | 1 | 0 | 0 |
| TGF | 2 | 0 | 0 | 0 | 0 |
| UNC | 0 | 0 | 0 | 0 | 0 |
| UNC(LP) | 5 | 1 | 0 | 1 | 3 |

Percentuali per riga (quota di ogni classe di Crupi finita in ciascuna classe predetta; la diagonale è la recall):

| Crupi | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 97.1% | 0.0% | 0.0% | 1.4% | 1.4% |
| SF | 0.0% | 80.0% | 20.0% | 0.0% | 0.0% |
| TGF | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC | — | — | — | — | — |
| UNC(LP) | 50.0% | 10.0% | 0.0% | 10.0% | 30.0% |

Percentuali per colonna (composizione di ogni classe predetta; la diagonale è la precision):

| Crupi | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 90.7% | 0.0% | 0.0% | 50.0% | 25.0% |
| SF | 0.0% | 80.0% | 100.0% | 0.0% | 0.0% |
| TGF | 2.7% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC(LP) | 6.7% | 20.0% | 0.0% | 50.0% | 75.0% |

Per classe (supporto = eventi con quella classe di Crupi):

| classe | supporto (Crupi) | predetti | corretti | recall % | precision % |
|---|---|---|---|---|---|
| GRB | 70 | 75 | 68 | 97.1% | 90.7% |
| SF | 5 | 5 | 4 | 80.0% | 80.0% |
| TGF | 2 | 1 | 0 | 0.0% | 0.0% |
| UNC | 0 | 2 | 0 | — | 0.0% |
| UNC(LP) | 10 | 4 | 3 | 30.0% | 75.0% |

Per regola, uno-contro-resto (come nello script di Crupi):

| regola | positivi Crupi | flag regola | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|
| GRB | 74 | 79 | 72 | 7 | 2 | 0.91 | 0.97 |
| SF | 6 | 6 | 5 | 1 | 1 | 0.83 | 0.83 |
| TGF | 3 | 4 | 1 | 3 | 2 | 0.25 | 0.33 |
| UNC(LP) | 10 | 15 | 8 | 7 | 2 | 0.53 | 0.80 |
| GF | 2 | 17 | 0 | 17 | 2 | 0.00 | 0.00 |

### 6.2 Tipo di trigger GBM contro classe predetta

Trigger del catalogo GBM abbinati a un nostro evento: 67 (verificato che ogni trigger cada nella finestra dell'evento a cui punta, tolleranza 8.192 s). Il **tipo GBM non è la natura fisica** dell'evento: è la classificazione del flight software e dei duty scientist (UNCERT e LOCLPAR sono incerti per definizione).

Conteggi (righe: tipo GBM; colonne: classe predetta):

| tipo GBM | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 57 | 0 | 0 | 1 | 1 |
| LOCLPAR | 2 | 0 | 0 | 0 | 1 |
| SFLARE | 0 | 4 | 1 | 0 | 0 |

Percentuali per riga:

| tipo GBM | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 96.6% | 0.0% | 0.0% | 1.7% | 1.7% |
| LOCLPAR | 66.7% | 0.0% | 0.0% | 0.0% | 33.3% |
| SFLARE | 0.0% | 80.0% | 20.0% | 0.0% | 0.0% |

Concordanza con una mappatura **IPOTETICA** (GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP), UNCERT→UNC): **62/67 (92.5%)**.

| tipo GBM | classe attesa (ipotesi) | abbinati | concordi | concordanza % |
|---|---|---|---|---|
| GRB | GRB | 59 | 57 | 96.6% |
| LOCLPAR | UNC(LP) | 3 | 1 | 33.3% |
| SFLARE | SF | 5 | 4 | 80.0% |

## 7. Localizzazione

Eseguita: posizione (PSO sulla risposta geometrica dei NaI) per 136/136 eventi, in `results/events_table_loc.csv`. **Non validata** rispetto a posizioni di riferimento: le coordinate servono come feature del classificatore (distanza da Sole e Terra), non come risultato.

## 8. Anomalie del motore

- Fondo previsto ≤ 0: 212 celle su 2238398 bin × 36 canali (6 bin con almeno un canale, 5 con tutti). Da engine v3 quei bin sono esclusi dal calcolo di S; gli eventi vicini hanno il flag `near_zero_prediction` (6, 9).
- Convergenza: val_loss finale 4.386, migliore 4.385 (epoca 57); MAE test/train mediano sui 36 canali 1.004. Controllo formale non registrato (bundle precedente all'introduzione del controllo).
- Passaggi SAA brevi non mascherati (buco ≤ 500 s): 45; la rete tende a sottostimare il fondo nell'avvicinamento (flag `saa_edge_short_passage`).
- Stabilità rispetto alla rete (stesso periodo): con `model_03-2019_07-2019_4.4_2026-09-21` (run `engine-v2`, 144 eventi): 126 coppie, 10 solo qui, 18 solo là.

## 9. Elenchi per nome

Tutti i trigger del catalogo GBM nei giorni con dati del periodo (`validation/list_gbm_grb.csv`, `validation/list_gbm_other.csv`). Esito: *rivelato* (abbinato a un nostro evento), *mancato* (dati presenti, nessun evento), *senza dati* (maschera SAA o buco).

### 9.1 GRB (93: rivelato 59, mancato 19, senza dati 15)

| trigger_name | trigger_time | T90_s | esito | evento_trig_ids | classe_predetta |
|---|---|---|---|---|---|
| bn190303240 | 2019-03-03 05:45:22.235 | 64.8 | rivelato | 1 | GRB |
| bn190304371 | 2019-03-04 08:54:35.515 | 62.2 | senza dati |  |  |
| bn190304818 | 2019-03-04 19:37:23.342 | 2.9 | rivelato | 2 | GRB |
| bn190306943 | 2019-03-06 22:37:43.178 | 180.5 | rivelato | 5 | GRB |
| bn190307151 | 2019-03-07 03:37:16.537 | 75.5 | rivelato | 7 | GRB |
| bn190308923 | 2019-03-08 22:09:46.740 | 45.6 | mancato |  |  |
| bn190310398 | 2019-03-10 09:32:32.569 | 59.4 | rivelato | 10 | GRB |
| bn190311600 | 2019-03-11 14:23:37.601 | 12.5 | mancato |  |  |
| bn190312446 | 2019-03-12 10:42:10.794 | 12.8 | rivelato | 14 | GRB |
| bn190315512 | 2019-03-15 12:17:42.138 | 29.2 | rivelato | 16 | GRB |
| bn190319353 | 2019-03-19 08:28:17.514 | 13.9 | senza dati |  |  |
| bn190319375 | 2019-03-19 09:00:37.980 | 21.8 | senza dati |  |  |
| bn190320052 | 2019-03-20 01:14:16.488 | 43.0 | rivelato | 19 | GRB |
| bn190321363 | 2019-03-21 08:42:33.858 | 55.8 | senza dati |  |  |
| bn190323179 | 2019-03-23 04:17:14.965 | 4.7 | senza dati |  |  |
| bn190323303 | 2019-03-23 07:16:51.688 | 30.5 | rivelato | 22 | GRB |
| bn190323548 | 2019-03-23 13:09:04.842 | 1.3 | mancato |  |  |
| bn190323879 | 2019-03-23 21:05:19.785 | 38.4 | rivelato | 23 | GRB |
| bn190324348 | 2019-03-24 08:21:09.629 | 52.2 | rivelato | 24 | GRB |
| bn190324947 | 2019-03-24 22:44:02.636 | 26.9 | mancato |  |  |
| bn190325999 | 2019-03-25 23:58:57.211 | 316.9 | rivelato | 26 | GRB |
| bn190326314 | 2019-03-26 07:31:38.998 | 55.8 | senza dati |  |  |
| bn190326975 | 2019-03-26 23:24:41.342 | 20.7 | rivelato | 27 | GRB |
| bn190327111 | 2019-03-27 02:39:10.973 | 36.9 | rivelato | 28 | GRB |
| bn190330694 | 2019-03-30 16:39:32.274 | 36.1 | rivelato | 31 | GRB |
| bn190331093 | 2019-03-31 02:14:37.572 | 4.8 | mancato |  |  |
| bn190401139 | 2019-04-01 03:20:20.538 | 42.8 | rivelato | 32 | GRB |
| bn190404293 | 2019-04-04 07:01:21.925 | 9.5 | mancato |  |  |
| bn190406450 | 2019-04-06 10:47:20.324 | 11.8 | rivelato | 37 | GRB |
| bn190406465 | 2019-04-06 11:09:47.053 | 15.1 | mancato |  |  |
| bn190406745 | 2019-04-06 17:52:33.155 | 80.4 | rivelato | 39 | GRB |
| bn190407575 | 2019-04-07 13:48:36.785 | 58.9 | rivelato | 41 | GRB |
| bn190407672 | 2019-04-07 16:07:26.493 | 17.7 | rivelato | 42 | GRB |
| bn190407788 | 2019-04-07 18:54:41.578 | 2.4 | senza dati |  |  |
| bn190409901 | 2019-04-09 21:38:05.455 | 1.6 | senza dati |  |  |
| bn190411407 | 2019-04-11 09:45:48.597 | 18.7 | rivelato | 47 | UNC(LP) |
| bn190411579 | 2019-04-11 13:53:58.091 | 60.9 | rivelato | 48 | GRB |
| bn190415173 | 2019-04-15 04:09:49.964 | 52.5 | rivelato | 52 | UNC |
| bn190419414 | 2019-04-19 09:55:37.770 | 212.7 | rivelato | 54 | GRB |
| bn190420981 | 2019-04-20 23:32:24.966 | 1.5 | rivelato | 57 | GRB |
| bn190422284 | 2019-04-22 06:48:17.495 | 80.4 | senza dati |  |  |
| bn190422670 | 2019-04-22 16:05:04.521 | 20.7 | rivelato | 58 | GRB |
| bn190422957 | 2019-04-22 22:58:24.004 | 213.3 | rivelato | 60 | GRB |
| bn190425089 | 2019-04-25 02:07:43.545 | 7.7 | mancato |  |  |
| bn190427190 | 2019-04-27 04:34:15.081 | 0.4 | senza dati |  |  |
| bn190428783 | 2019-04-28 18:48:12.460 | 16.6 | rivelato | 64 | GRB |
| bn190429743 | 2019-04-29 17:49:50.579 | 22.3 | rivelato | 66 | GRB |
| bn190501794 | 2019-05-01 19:03:42.592 | 425.0 | mancato |  |  |
| bn190502168 | 2019-05-02 04:01:30.415 | 11.8 | rivelato | 68 | GRB |
| bn190504415 | 2019-05-04 09:57:34.203 | 77.6 | rivelato | 69 | GRB |
| bn190504678 | 2019-05-04 16:16:28.313 | 0.7 | mancato |  |  |
| bn190505051 | 2019-05-05 01:14:09.330 | 0.0 | senza dati |  |  |
| bn190507270 | 2019-05-07 06:28:23.301 | 85.0 | rivelato | 74 | GRB |
| bn190507712 | 2019-05-07 17:05:16.938 | 0.1 | mancato |  |  |
| bn190507970 | 2019-05-07 23:16:29.638 | 36.4 | rivelato | 76 | GRB |
| bn190508808 | 2019-05-08 19:22:50.400 | 37.6 | rivelato | 77 | GRB |
| bn190508987 | 2019-05-08 23:41:24.148 | 119.8 | senza dati |  |  |
| bn190510120 | 2019-05-10 02:52:13.232 | 69.6 | senza dati |  |  |
| bn190510430 | 2019-05-10 10:19:16.044 | 0.6 | rivelato | 79 | GRB |
| bn190511302 | 2019-05-11 07:14:24.358 | 27.6 | rivelato | 80 | GRB |
| bn190512611 | 2019-05-12 14:39:59.722 | 28.2 | rivelato | 81 | GRB |
| bn190515190 | 2019-05-15 04:33:03.135 | 1.3 | mancato |  |  |
| bn190517813 | 2019-05-17 19:30:10.172 | 4.9 | rivelato | 89 | GRB |
| bn190519309 | 2019-05-19 07:24:57.343 | 43.5 | rivelato | 90 | GRB |
| bn190525032 | 2019-05-25 00:45:47.652 | 0.9 | mancato |  |  |
| bn190530430 | 2019-05-30 10:19:08.903 | 18.4 | rivelato | 102 | GRB |
| bn190531312 | 2019-05-31 07:29:11.825 | 57.1 | rivelato | 103 | GRB |
| bn190531568 | 2019-05-31 13:38:03.822 | 0.3 | mancato |  |  |
| bn190531840 | 2019-05-31 20:10:12.142 | 38.1 | rivelato | 104 | GRB |
| bn190601325 | 2019-06-01 07:47:24.176 | 0.6 | mancato |  |  |
| bn190603795 | 2019-06-03 19:04:25.984 | 22.5 | rivelato | 106 | GRB |
| bn190604446 | 2019-06-04 10:42:37.054 | 32.0 | rivelato | 107 | GRB |
| bn190605974 | 2019-06-05 23:22:27.118 | 3.6 | rivelato | 108 | GRB |
| bn190606080 | 2019-06-06 01:55:07.776 | 0.2 | rivelato | 109 | GRB |
| bn190607071 | 2019-06-07 01:42:44.289 | 37.9 | rivelato | 112 | GRB |
| bn190608009 | 2019-06-08 00:12:18.394 | 85.2 | rivelato | 113 | GRB |
| bn190609315 | 2019-06-09 07:34:05.259 | 97.5 | rivelato | 117 | GRB |
| bn190610750 | 2019-06-10 17:59:49.908 | 37.9 | mancato |  |  |
| bn190610834 | 2019-06-10 20:00:23.685 | 3.1 | mancato |  |  |
| bn190611950 | 2019-06-11 22:47:49.337 | 100.6 | rivelato | 119 | GRB |
| bn190612165 | 2019-06-12 03:57:24.648 | 144.9 | rivelato | 120 | GRB |
| bn190613172 | 2019-06-13 04:07:18.234 | 17.1 | rivelato | 122 | GRB |
| bn190613449 | 2019-06-13 10:47:00.049 | 4.9 | rivelato | 123 | GRB |
| bn190615636 | 2019-06-15 15:16:27.372 | 16.9 | rivelato | 125 | GRB |
| bn190619018 | 2019-06-19 00:26:01.777 | 177.9 | rivelato | 127 | GRB |
| bn190619595 | 2019-06-19 14:16:25.891 | 134.9 | rivelato | 128 | GRB |
| bn190620507 | 2019-06-20 12:10:10.809 | 51.7 | rivelato | 129 | GRB |
| bn190622368 | 2019-06-22 08:50:06.276 | 31.7 | mancato |  |  |
| bn190623461 | 2019-06-23 11:03:27.095 | 9.7 | senza dati |  |  |
| bn190626254 | 2019-06-26 06:06:21.684 | 23.8 | rivelato | 131 | GRB |
| bn190627481 | 2019-06-27 11:31:59.942 | 9.0 | mancato |  |  |
| bn190628521 | 2019-06-28 12:30:55.320 | 19.2 | rivelato | 133 | GRB |
| bn190630257 | 2019-06-30 06:09:58.319 | 0.2 | senza dati |  |  |

### 9.2 Trigger non-GRB (50: mancato 34, senza dati 8, rivelato 8)

| tipo | trigger_name | trigger_time | T90_s | esito | evento_trig_ids | classe_predetta |
|---|---|---|---|---|---|---|
| TGF | bn190301418 | 2019-03-01 10:01:15.656 |  | mancato |  |  |
| TGF | bn190304208 | 2019-03-04 04:59:50.498 |  | mancato |  |  |
| UNCERT | bn190306960 | 2019-03-06 23:02:40.420 |  | mancato |  |  |
| TGF | bn190311817 | 2019-03-11 19:36:13.000 |  | mancato |  |  |
| LOCLPAR | bn190313150 | 2019-03-13 03:36:00.811 |  | senza dati |  |  |
| TGF | bn190315717 | 2019-03-15 17:12:28.119 |  | mancato |  |  |
| TGF | bn190317700 | 2019-03-17 16:48:02.389 |  | mancato |  |  |
| TGF | bn190319608 | 2019-03-19 14:35:16.031 |  | mancato |  |  |
| LOCLPAR | bn190320018 | 2019-03-20 00:26:25.614 |  | senza dati |  |  |
| SFLARE | bn190321613 | 2019-03-21 14:42:03.222 |  | rivelato | 21 | TGF |
| UNCERT | bn190326747 | 2019-03-26 17:55:54.016 |  | mancato |  |  |
| TGF | bn190330372 | 2019-03-30 08:55:36.932 |  | mancato |  |  |
| UNCERT | bn190401410 | 2019-04-01 09:51:05.036 |  | mancato |  |  |
| TGF | bn190402512 | 2019-04-02 12:16:50.443 |  | mancato |  |  |
| LOCLPAR | bn190408536 | 2019-04-08 12:52:18.176 |  | rivelato | 43 | GRB |
| TGF | bn190417464 | 2019-04-17 11:08:18.409 |  | senza dati |  |  |
| TGF | bn190418919 | 2019-04-18 22:04:03.328 |  | mancato |  |  |
| UNCERT | bn190505818 | 2019-05-05 19:37:53.664 |  | mancato |  |  |
| SFLARE | bn190506213 | 2019-05-06 05:06:58.378 |  | rivelato | 70 | SF |
| SFLARE | bn190506577 | 2019-05-06 13:51:23.127 |  | rivelato | 71 | SF |
| SFLARE | bn190506742 | 2019-05-06 17:48:10.111 |  | rivelato | 72 | SF |
| TGF | bn190508107 | 2019-05-08 02:34:25.790 |  | mancato |  |  |
| SFLARE | bn190509239 | 2019-05-09 05:43:55.583 |  | rivelato | 78 | SF |
| TGF | bn190509787 | 2019-05-09 18:53:14.298 |  | mancato |  |  |
| LOCLPAR | bn190511253 | 2019-05-11 06:03:42.924 |  | senza dati |  |  |
| TGF | bn190512623 | 2019-05-12 14:56:32.167 |  | mancato |  |  |
| LOCLPAR | bn190513824 | 2019-05-13 19:47:08.098 |  | senza dati |  |  |
| TGF | bn190514672 | 2019-05-14 16:07:23.939 |  | mancato |  |  |
| TGF | bn190514901 | 2019-05-14 21:38:02.170 |  | mancato |  |  |
| TGF | bn190515435 | 2019-05-15 10:26:12.748 |  | mancato |  |  |
| TGF | bn190515487 | 2019-05-15 11:41:49.478 |  | mancato |  |  |
| TGF | bn190515824 | 2019-05-15 19:46:58.291 |  | mancato |  |  |
| TGF | bn190517095 | 2019-05-17 02:17:06.248 |  | mancato |  |  |
| LOCLPAR | bn190520598 | 2019-05-20 14:21:48.797 |  | rivelato | 94 | GRB |
| UNCERT | bn190525500 | 2019-05-25 12:00:34.477 |  | mancato |  |  |
| TGF | bn190525670 | 2019-05-25 16:04:15.673 |  | mancato |  |  |
| TGF | bn190531540 | 2019-05-31 12:58:17.211 |  | mancato |  |  |
| TGF | bn190604577 | 2019-06-04 13:51:30.894 |  | mancato |  |  |
| LOCLPAR | bn190608859 | 2019-06-08 20:36:53.357 |  | rivelato | 115 | UNC(LP) |
| TGF | bn190610277 | 2019-06-10 06:38:13.564 |  | senza dati |  |  |
| TGF | bn190611194 | 2019-06-11 04:39:20.209 |  | mancato |  |  |
| TGF | bn190612260 | 2019-06-12 06:13:49.611 |  | senza dati |  |  |
| TGF | bn190613961 | 2019-06-13 23:03:30.952 |  | mancato |  |  |
| UNCERT | bn190619235 | 2019-06-19 05:38:03.136 |  | mancato |  |  |
| UNCERT | bn190620579 | 2019-06-20 13:53:27.802 |  | mancato |  |  |
| UNCERT | bn190620772 | 2019-06-20 18:31:24.279 |  | mancato |  |  |
| UNCERT | bn190620907 | 2019-06-20 21:46:33.246 |  | mancato |  |  |
| TGF | bn190622029 | 2019-06-22 00:41:37.810 |  | senza dati |  |  |
| UNCERT | bn190624976 | 2019-06-24 23:25:16.658 |  | mancato |  |  |
| UNCERT | bn190626526 | 2019-06-26 12:36:48.943 |  | mancato |  |  |

### 9.3 Eventi di Crupi in finestra (95: ritrovato 91, non ritrovato 4; `validation/list_crupi_events.csv`)

| insieme | id | nome_catalogo | trigger_time_utc | CE_Crupi | esito | evento_trig_ids | classe_predetta | diagnosi |
|---|---|---|---|---|---|---|---|---|
| noto | 2019_1 | GRB190303240 | 2019-03-03 05:45:19 | R | ritrovato | 1 | GRB |  |
| noto | 2019_2 | GRB190304818 | 2019-03-04 19:37:21 | P | ritrovato | 2 | GRB |  |
| noto | 2019_4 | GRB190306943 | 2019-03-06 22:37:42 | R | ritrovato | 5 | GRB |  |
| noto | 2019_5 | GRB190307151 | 2019-03-07 03:37:19 | R | ritrovato | 7 | GRB |  |
| noto | 2019_6 | GRB190310398 | 2019-03-10 09:32:35 | R | ritrovato | 10 | GRB |  |
| noto | 2019_7 | GRB190311600 | 2019-03-11 14:23:37 | P | non ritrovato |  |  | below threshold: max FOCuS r1 within ±60 s = 2.96 sigma |
| noto | 2019_8 | GRB190312446 | 2019-03-12 10:42:13 | R | ritrovato | 14 | GRB |  |
| noto | 2019_10 | GRB190315512 | 2019-03-15 12:17:44 | R | ritrovato | 16 | GRB |  |
| noto | 2019_12 | GRB190320052 | 2019-03-20 01:14:21 | R | ritrovato | 19 | GRB |  |
| noto | 2019_13 | SFLARE19032161 | 2019-03-21 14:42:05 | R | ritrovato | 21 | TGF |  |
| noto | 2019_14 | GRB190323303 | 2019-03-23 07:16:50 | R | ritrovato | 22 | GRB |  |
| noto | 2019_15 | GRB190323879 | 2019-03-23 21:05:18 | R | ritrovato | 23 | GRB |  |
| noto | 2019_16 | GRB190324348 | 2019-03-24 08:21:13 | R | ritrovato | 24 | GRB |  |
| noto | 2019_17 | GRB190324947 | 2019-03-24 22:44:17 | R | ritrovato | 25 | GRB |  |
| noto | 2019_18 | GRB190325999 | 2019-03-25 23:58:59 | R | ritrovato | 26 | GRB |  |
| noto | 2019_19 | GRB190326975 | 2019-03-26 23:24:43 | R | ritrovato | 27 | GRB |  |
| noto | 2019_20 | GRB190327111 | 2019-03-27 02:39:13 | R | ritrovato | 28 | GRB |  |
| noto | 2019_22 | GRB190330694 | 2019-03-30 16:39:28 | R | ritrovato | 31 | GRB |  |
| noto | 2019_23 | GRB190401139 | 2019-04-01 03:20:19 | R | ritrovato | 32 | GRB |  |
| noto | 2019_27 | GRB190406450 | 2019-04-06 10:47:22 | R | ritrovato | 37 | GRB |  |
| noto | 2019_28 | GRB190406745 | 2019-04-06 17:52:31 | R | ritrovato | 39 | GRB |  |
| noto | 2019_29 | GRB190407575 | 2019-04-07 13:48:39 | R | ritrovato | 41 | GRB |  |
| noto | 2019_30 | GRB190407672 | 2019-04-07 16:07:29 | R | ritrovato | 42 | GRB |  |
| noto | 2019_31 | LOCLPAR1904085 | 2019-04-08 12:51:22 | R | ritrovato | 43 | GRB |  |
| noto | 2019_32 | GRB190411407 | 2019-04-11 09:45:46 | R | ritrovato | 47 | UNC(LP) |  |
| noto | 2019_33 | GRB190411579 | 2019-04-11 13:53:56 | R | ritrovato | 48 | GRB |  |
| noto | 2019_34 | GRB190415173 | 2019-04-15 04:09:46 | R | ritrovato | 52 | UNC |  |
| noto | 2019_35 | GRB190419414 | 2019-04-19 09:55:40 | R | ritrovato | 54 | GRB |  |
| noto | 2019_38 | GRB190420981 | 2019-04-20 23:32:27 | P | ritrovato | 57 | GRB |  |
| noto | 2019_39 | GRB190422670 | 2019-04-22 16:05:09 | S | ritrovato | 58 | GRB |  |
| noto | 2019_41 | GRB190422957 | 2019-04-22 22:56:09 | R | ritrovato | 60 | GRB |  |
| noto | 2019_43 | GRB190428783 | 2019-04-28 18:48:11 | R | ritrovato | 64 | GRB |  |
| noto | 2019_44 | GRB190429743 | 2019-04-29 17:49:54 | S | ritrovato | 66 | GRB |  |
| noto | 2019_45 | GRB190502168 | 2019-05-02 04:01:32 | R | ritrovato | 68 | GRB |  |
| noto | 2019_46 | GRB190504415 | 2019-05-04 09:57:36 | P | ritrovato | 69 | GRB |  |
| noto | 2019_47 | SFLARE19050621 | 2019-05-06 05:07:05 | R | ritrovato | 70 | SF |  |
| noto | 2019_48 | SFLARE19050657 | 2019-05-06 13:53:21 | R | ritrovato | 71 | SF |  |
| noto | 2019_49 | SFLARE19050674 | 2019-05-06 17:47:45 | R | ritrovato | 72 | SF |  |
| noto | 2019_50 | GRB190507270 | 2019-05-07 06:28:19 | R | ritrovato | 74 | GRB |  |
| noto | 2019_52 | GRB190507970 | 2019-05-07 23:16:29 | R | ritrovato | 76 | GRB |  |
| noto | 2019_53 | GRB190508808 | 2019-05-08 19:22:49 | R | ritrovato | 77 | GRB |  |
| noto | 2019_54 | SFL190509239 | 2019-05-09 05:44:02 | R | ritrovato | 78 | SF |  |
| noto | 2019_55 | GRB190510430 | 2019-05-10 10:12:57 | R | ritrovato | 79 | GRB |  |
| noto | 2019_56 | GRB190511302 | 2019-05-11 07:14:26 | R | ritrovato | 80 | GRB |  |
| noto | 2019_57 | GRB190512611 | 2019-05-12 14:40:04 | R | ritrovato | 81 | GRB |  |
| noto | 2019_62 | TGF190514901 | 2019-05-14 21:41:40 | P | ritrovato | 86 | GRB |  |
| noto | 2019_64 | GRB190517813 | 2019-05-17 19:30:08 | R | ritrovato | 89 | GRB |  |
| noto | 2019_65 | GRB190519309 | 2019-05-19 07:24:53 | R | ritrovato | 90 | GRB |  |
| noto | 2019_67 | LOCLPAR1905205 | 2019-05-20 14:21:05 | R | ritrovato | 94 | GRB |  |
| noto | 2019_70 | GRB190530430 | 2019-05-30 10:19:05 | R | ritrovato | 102 | GRB |  |
| noto | 2019_71 | GRB190531312 | 2019-05-31 07:29:10 | R | ritrovato | 103 | GRB |  |
| noto | 2019_72 | GRB190531840 | 2019-05-31 20:10:02 | R | ritrovato | 104 | GRB |  |
| noto | 2019_73 | GRB190603795 | 2019-06-03 19:04:31 | R | ritrovato | 106 | GRB |  |
| noto | 2019_74 | GRB190604446 | 2019-06-04 10:42:33 | R | ritrovato | 107 | GRB |  |
| noto | 2019_75 | GRB190605974 | 2019-06-05 23:22:29 | S | ritrovato | 108 | GRB |  |
| noto | 2019_76 | GRB190606080 | 2019-06-06 01:55:04 | R | ritrovato | 109 | GRB |  |
| noto | 2019_78 | GRB190607071 | 2019-06-07 01:42:46 | R | ritrovato | 112 | GRB |  |
| noto | 2019_79 | GRB190608009 | 2019-06-08 00:12:20 | R | ritrovato | 113 | GRB |  |
| noto | 2019_82 | LOCLPAR1906088 | 2019-06-08 20:35:08 | R | ritrovato | 115 | UNC(LP) |  |
| noto | 2019_83 | GRB190609315 | 2019-06-09 07:33:36 | R | ritrovato | 117 | GRB |  |
| noto | 2019_84 | GRB190610750 | 2019-06-10 18:00:05 | R | ritrovato | 118 | GRB |  |
| noto | 2019_85 | GRB190611950 | 2019-06-11 22:47:46 | R | ritrovato | 119 | GRB |  |
| noto | 2019_86 | GRB190612165 | 2019-06-12 03:57:24 | R | ritrovato | 120 | GRB |  |
| noto | 2019_87 | GRB190613172 | 2019-06-13 04:07:21 | R | ritrovato | 122 | GRB |  |
| noto | 2019_88 | GRB190613449 | 2019-06-13 10:46:58 | R | ritrovato | 123 | GRB |  |
| noto | 2019_89 | GRB190615636 | 2019-06-15 15:16:26 | R | ritrovato | 125 | GRB |  |
| noto | 2019_90 | GRB190619018 | 2019-06-19 00:24:24 | R | ritrovato | 127 | GRB |  |
| noto | 2019_91 | GRB190619595 | 2019-06-19 14:15:55 | R | ritrovato | 128 | GRB |  |
| noto | 2019_92 | GRB190620507 | 2019-06-20 12:10:10 | R | ritrovato | 129 | GRB |  |
| noto | 2019_93 | GRB190626254 | 2019-06-26 06:06:24 | P | ritrovato | 131 | GRB |  |
| noto | 2019_95 | GRB190628521 | 2019-06-28 12:30:54 | R | ritrovato | 133 | GRB |  |
| inedito | 2019_0 | UNKNOWN: UNC(LP) | 2019-03-01 09:28:28 | P | non ritrovato |  |  | below threshold: max FOCuS r1 within ±60 s = 1.65 sigma |
| inedito | 2019_3 | UNKNOWN: UNC(LP) | 2019-03-06 06:45:30 | R | ritrovato | 4 | UNC(LP) |  |
| inedito | 2019_9 | UNKNOWN: GRB | 2019-03-15 05:09:11 | R | ritrovato | 15 | GRB |  |
| inedito | 2019_11 | UNKNOWN: GRB | 2019-03-17 01:08:06 | P | ritrovato | 18 | GRB |  |
| inedito | 2019_21 | UNKNOWN: GRB | 2019-03-27 06:36:04 | P | ritrovato | 29 | GRB |  |
| inedito | 2019_24 | UNKNOWN: SF/GRB | 2019-04-04 12:24:17 | R | ritrovato | 33 | GRB |  |
| inedito | 2019_25 | UNKNOWN: GRB | 2019-04-04 13:08:07 | S | ritrovato | 34 | GRB |  |
| inedito | 2019_26 | UNKNOWN: UNC(LP) | 2019-04-04 13:45:40 | R | ritrovato | 35 | GRB |  |
| inedito | 2019_36 | UNKNOWN: GRB/GF | 2019-04-20 15:08:24 | S | ritrovato | 55 | GRB |  |
| inedito | 2019_37 | UNKNOWN: GRB | 2019-04-20 22:32:56 | R | ritrovato | 56 | GRB |  |
| inedito | 2019_42 | UNKNOWN: UNC(LP) | 2019-04-28 00:16:26 | R | ritrovato | 63 | GRB |  |
| inedito | 2019_51 | UNKNOWN: TGF | 2019-05-07 17:15:13 | P | ritrovato | 75 | GRB |  |
| inedito | 2019_58 | UNKNOWN: TGF | 2019-05-14 07:38:41 | P | non ritrovato |  |  | below threshold: max FOCuS r1 within ±60 s = 2.87 sigma |
| inedito | 2019_59 | UNKNOWN: UNC(LP) | 2019-05-14 10:31:29 | R | ritrovato | 82 | GRB |  |
| inedito | 2019_60 | UNKNOWN: UNC(LP) | 2019-05-14 11:59:58 | R | ritrovato | 84 | UNC |  |
| inedito | 2019_61 | UNKNOWN: UNC(LP) | 2019-05-14 13:45:47 | R | ritrovato | 85 | SF |  |
| inedito | 2019_63 | UNKNOWN: GRB | 2019-05-15 16:04:20 | P | ritrovato | 88 | GRB |  |
| inedito | 2019_66 | UNKNOWN: GRB | 2019-05-20 05:34:01 | R | ritrovato | 92 | GRB |  |
| inedito | 2019_68 | UNKNOWN: GRB | 2019-05-24 11:15:53 | S | ritrovato | 97 | GRB |  |
| inedito | 2019_69 | UNKNOWN: GRB/TGF | 2019-05-28 23:32:56 | P | ritrovato | 99 | GRB |  |
| inedito | 2019_77 | UNKNOWN: GRB/GF | 2019-06-06 13:21:42 | R | ritrovato | 110 | GRB |  |
| inedito | 2019_80 | UNKNOWN: UNC(LP) | 2019-06-08 20:22:43 | R | ritrovato | 115 | UNC(LP) |  |
| inedito | 2019_81 | UNKNOWN: UNC(LP) | 2019-06-08 20:23:03 | R | non ritrovato |  |  | detected but merged: inside our event 115, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |
| inedito | 2019_94 | UNKNOWN: GRB | 2019-06-28 04:23:34 | P | ritrovato | 132 | GRB |  |
