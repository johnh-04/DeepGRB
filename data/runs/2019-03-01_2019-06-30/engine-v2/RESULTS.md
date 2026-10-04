# Resoconto della run `engine-v2` (2019-03-01 → 2019-06-30)

Generato da `benchmark/report.py` (step 9 di `pipeline/pipeline_bkg.py`); validazione del 2026-10-04 16:39 UTC, commit `98d3c97c11`. Tutti i numeri sono letti da file della run; le tabelle complete sono in `validation/` e `results/`.

## 1. Run, rete e parametri

- Periodo: **2019-03-01 → 2019-06-30** (giorni UTC inclusi); run `data/runs/2019-03-01_2019-06-30/engine-v2`.
- Motore: engine v2; esecuzioni: 2026-10-03 13:21 commit `1dfb652201`.
- Rete: bundle `data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21`; seed di training non registrato (modello legacy); checksum sha256 del bundle `non registrato`.
- Addestramento: trained by upstream-equivalent code (b0b2802); scaler refitted with split_seed.
- Parametri: bin 4.096 s; FOCuS mu_min 1.2, t_max 50 bin (ingresso: rates (counts/s)); soglia 3.0 σ in r1 su ≥ 1 rivelatori; merge 600 s; maschera SAA ±150 bin attorno ai buchi > 500 s.

## 2. Eventi

- Totale: **144**; tier CE: R 105, S 18, P 21 (R: più rivelatori e più bande; S: più rivelatori, una banda; P: gli altri).
- Abbinati al catalogo trigger GBM: 68; a Crupi noti: 70; a Crupi inediti: 21. Senza controparte: **53** (0.43 al giorno su 122 giorni con dati).

## 3. Catalogo ufficiale Fermi-GBM

Regola primaria: abbinamento uno-a-uno, istante del trigger entro [inizio evento − 8.192 s, fine evento + 8.192 s].

- Trigger nel periodo, nei giorni con dati: 143; senza dati validi all'istante (maschera SAA/buchi): 23; disponibili: 120; rivelati: **68**.
- Entro ±150 s da un buco > 500 s: 8 trigger.

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 60 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

GRB del Burst Catalog (T90):

|  | questa run | paper (fino al 9/07/2019) |
|---|---|---|
| GRB nel periodo | 93 | 96 |
| senza dati (SAA) | 15 | 15 |
| rivelati / disponibili | 60/78 (76.9%) | 65/81 |
| T90 > 4.096 s | 54/65 (83.1%) | 60/68 (88%) |
| T90 ≤ 4.096 s | 6/13 (46.2%) | 5/13 (34%) |

Sensibilità alla regola di abbinamento:

| margine | GBM rivelati/disponibili | GRB | Crupi noti | Crupi inediti |
|---|---|---|---|---|
| primary (2 bins) | 68/120 | 60/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 10 s | 68/120 | 60/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 60 s | 71/120 | 63/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 1200 s | 73/120 | 64/78 | 70/71 (98.6%) | 22/24 (91.7%) |

## 4. Confronto con Crupi et al. (2023)

| criterio (docs/WORKING_RULES.md §6) | misurato | esito |
|---|---|---|
| Noti di Crupi ritrovati ≥ 90% | 70/71 (98.6%) | ✔ |
| Tutti gli R e S noti ritrovati | 65/65 (100.0%) | ✔ |
| Inediti R+S ritrovati ≥ 90% | 15/16 (93.8%) | ✔ |
| Inediti complessivi ≥ 70% | 21/24 (87.5%) | ✔ |
| Recall GRB T90 > 4.096 s ~ 88% (paper) | 54/65 (83.1%) | ordine di grandezza |
| Recall GRB T90 ≤ 4.096 s ~ 34% (paper) | 6/13 (46.2%) | ordine di grandezza |
| Numero eventi ~ 100 (paper, fino al 9 luglio) | 144 | informativo: dipende dalla rete |

- Noti (Tabella 11; in finestra 71 di 74): ritrovati **70/71 (98.6%)**; per tier: R 62/62, S 3/3, P 5/6.
- Inediti (Tabella 10; in finestra 24 di 25): ritrovati **21/24 (87.5%)**; per tier: R 12/13, S 3/3, P 6/8.

Noti non ritrovati:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_7 | 2019-03-11 14:23:37 | n8 | GRB190311600 | 3.36 | P | True | 2.82 | 47274.62 | below threshold: max FOCuS r1 within ±60 s = 2.82 sigma |

Inediti non ritrovati:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_0 | 2019-03-01 09:28:28 | n6 | UNKNOWN: UNC(LP) | 3.63 | P | True | 2.45 | -929.47 | below threshold: max FOCuS r1 within ±60 s = 2.45 sigma |
| 2019_58 | 2019-05-14 07:38:41 | na | UNKNOWN: TGF | 3.09 | P | True | 2.97 | 10307.34 | below threshold: max FOCuS r1 within ±60 s = 2.97 sigma |
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 9.99 | -228.48 | detected but merged: inside our event 122, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

Significatività, nostro S rispetto a quello di Crupi (eventi abbinati con S di riferimento numerico):

| banda | eventi | mediana S_nostro/S_Crupi | 16° pct | 84° pct |
|---|---|---|---|---|
| r0 | 31 | 1.02 | 0.89 | 1.10 |
| r1 | 33 | 1.03 | 0.95 | 1.15 |
| r2 | 9 | 0.76 | 0.67 | 0.92 |

Casi del §1 di docs/WORKING_RULES.md (i due "sub-threshold GRB" del vecchio log):

| tempo (§1) | trigger GBM | trigger_time | rivelato (regola primaria) | evento | inizio evento - trigger [s] | eventi nostri entro ±60 s | in tabelle Crupi |
|---|---|---|---|---|---|---|---|
| 2019-03-08 22:10:12 | GRB190308923 | 2019-03-08 22:09:46.740 | False |  |  | 1 | False |
| 2019-05-25 00:45:54 | GRB190525032 | 2019-05-25 00:45:47.652 | True | 102.00 | -3.41 | 1 | False |

## 5. Eventi senza controparte e flag di post-processing

Gli eventi senza controparte (né catalogo GBM né tabelle di Crupi) **non sono scoperte**: sono candidati da verificare. I flag aggiungono colonne e non cambiano l'elenco degli eventi (definizioni in `models/flags.py` e `docs/ORBIT_ANALYSIS.md`): `saa_edge_short_passage` (inizio entro 200 s da un passaggio SAA il cui buco non è mascherato), `saa_region_proximity` (Fermi entro 3.5° dalla regione SAA), `near_zero_prediction` (evento ±5 bin che tocca un bin con fondo previsto ≤ 0).

| eventi | n | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | almeno uno |
|---|---|---|---|---|---|
| abbinati Crupi/GBM | 91 | 0 | 1 | 0 | 1 |
| senza controparte | 53 | 24 | 38 | 0 | 38 |
| tutti | 144 | 24 | 39 | 0 | 39 |

Eventi senza controparte (53) per combinazione di flag:

| flag | eventi |
|---|---|
| saa_edge_short_passage, saa_region_proximity | 24 |
| nessuno | 15 |
| saa_region_proximity | 14 |

Tier: R 31, S 12, P 10; distanza dal buco SAA più vicino: minima 672 s, mediana 5218 s. Elenco completo: `validation/events_without_counterpart.csv`.

## 6. Classificazione (baseline euristica di Crupi)

Regole della "manual classification logic" di Crupi (`pipeline/script_classification2.py` upstream): soglie lette da decision tree uno-contro-resto e rifinite a mano. Baseline volutamente semplice, da superare con XGBoost (fase 6). Mancano la regola FP e le feature `fe_*` (tsfel). Il classificatore non legge le colonne del catalogo (`tests/test_classifier.py`). Fuori dai GRB è debole.

Classi predette su tutti gli eventi: GRB 109, UNC(LP) 18, TGF 6, SF 5, UNC 4, GF 2.

Su 91 eventi abbinati a Crupi, classe predetta tra quelle tentative di Crupi: 79/91 (86.8%).

Per regola, uno-contro-resto:

| regola | positivi Crupi | flag regola | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|
| GRB | 74 | 79 | 72 | 7 | 2 | 0.91 | 0.97 |
| SF | 6 | 6 | 5 | 1 | 1 | 0.83 | 0.83 |
| TGF | 3 | 3 | 1 | 2 | 2 | 0.33 | 0.33 |
| UNC(LP) | 10 | 15 | 8 | 7 | 2 | 0.53 | 0.80 |
| GF | 2 | 15 | 0 | 15 | 2 | 0.00 | 0.00 |

Matrice di confusione sugli eventi con classe Crupi univoca (87; righe Crupi, colonne predetta):

```
         GRB  SF  TGF  UNC  UNC(LP)
Crupi                              
GRB       68   0    0    1        1
SF         0   4    1    0        0
TGF        2   0    0    0        0
UNC        0   0    0    0        0
UNC(LP)    5   1    0    1        3
```

## 7. Localizzazione

Eseguita: posizione (PSO sulla risposta geometrica dei NaI) per 144/144 eventi, in `results/events_table_loc.csv`. **Non validata** rispetto a posizioni di riferimento: le coordinate servono come feature del classificatore (distanza da Sole e Terra), non come risultato.

## 8. Anomalie del motore

- Fondo previsto ≤ 0: conteggio non registrato nel manifest.
- Convergenza: storia dell'addestramento non registrata (modello legacy).
- Passaggi SAA brevi non mascherati (buco ≤ 500 s): 45; la rete tende a sottostimare il fondo nell'avvicinamento (flag `saa_edge_short_passage`).
- Stabilità rispetto alla rete (stesso periodo): con `model_2019-03-01_2019-06-30_seed1` (run `engine-v2-seed1`, 136 eventi): 126 coppie, 18 solo qui, 10 solo là.
