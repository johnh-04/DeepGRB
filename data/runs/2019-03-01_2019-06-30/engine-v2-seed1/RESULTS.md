# Resoconto della run `engine-v2-seed1` (2019-03-01 → 2019-06-30)

Generato da `benchmark/report.py` (step 9 di `pipeline/pipeline_bkg.py`); validazione del 2026-10-04 16:40 UTC, commit `98d3c97c11`. Tutti i numeri sono letti da file della run; le tabelle complete sono in `validation/` e `results/`.

## 1. Run, rete e parametri

- Periodo: **2019-03-01 → 2019-06-30** (giorni UTC inclusi); run `data/runs/2019-03-01_2019-06-30/engine-v2-seed1`.
- Motore: engine v2; esecuzioni: 2026-10-04 07:43 commit `c244881db8`.
- Rete: bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1`; seed di training 1; checksum sha256 del bundle `non registrato`.
- Addestramento: 64 epoche (migliore 57), 2048 unità, lr 0.0008, batch 2048, 378.0 s su /physical_device:GPU:0.
- Parametri: bin 4.096 s; FOCuS mu_min 1.2, t_max 50 bin (ingresso: rates (counts/s)); soglia 3.0 σ in r1 su ≥ 1 rivelatori; merge 600 s; maschera SAA ±150 bin attorno ai buchi > 500 s.

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

_Step 6 non eseguito: `results/events_classified.csv` assente._

## 7. Localizzazione

Non eseguita (`results/events_table_loc.csv` assente).

## 8. Anomalie del motore

- Fondo previsto ≤ 0: conteggio non registrato nel manifest.
- Convergenza: val_loss finale 4.386, migliore 4.385 (epoca 57); MAE test/train mediano sui 36 canali 1.004. Controllo formale non registrato (bundle precedente all'introduzione del controllo).
- Passaggi SAA brevi non mascherati (buco ≤ 500 s): 45; la rete tende a sottostimare il fondo nell'avvicinamento (flag `saa_edge_short_passage`).
- Stabilità rispetto alla rete (stesso periodo): con `model_03-2019_07-2019_4.4_2026-09-21` (run `engine-v2`, 144 eventi): 126 coppie, 10 solo qui, 18 solo là.
