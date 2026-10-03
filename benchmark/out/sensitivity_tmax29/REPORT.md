# Validazione baseline 2019

Generato da `python -m benchmark.validate` il 2026-10-03 13:47 UTC. Tutte le cifre sono calcolate da file su disco.

## Contesto

- Periodo: 2019-03-01 → 2019-06-30 (inclusivo); giorni con dati: 122.
- Run: `data/runs/2019-03-01_2019-06-30/engine-v2-sens-tmax29`; motore prodotto dal commit `1dfb652201332dbc801553d4e3cc1f30a81160b5` (codice modificato: False).
- Validazione eseguita dal commit `a3250c029daab2e9b878ab1ce0cef339c476f726`; Python 3.9.23, pandas 1.5.3, numpy 1.26.4.
- Modello: `data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21`; seed di training 0 (modello legacy: addestrato una volta, seed non registrato).
- Parametri del motore: soglia 3.0 σ in r1, mu_min 1.2, t_max 29 bin, esclusione SAA ±150 bin, merge 600 s.
- Matching: uno-a-uno; un riferimento è abbinato se il suo istante cade in [inizio evento − 8.192 s, fine evento + 8.192 s]; l'inizio evento è il change point FOCuS (`start_times_offset`).

## Criteri di accettazione (docs/WORKING_RULES.md §6, finestra al 30 giugno)

| criterio | misurato | esito |
|---|---|---|
| Noti di Crupi ritrovati ≥ 90% (≥ 64/71) | 70/71 (98.6%) | OK |
| Tutti gli R e S noti ritrovati (65) | 65/65 (100.0%) | OK |
| Inediti R+S ritrovati ≥ 90% (≥ 15/16) | 15/16 (93.8%) | OK |
| Inediti complessivi ≥ 70% (≥ 17/24) | 21/24 (87.5%) | OK |
| Recall GRB T90 > 4.096 s ~ 88% | 54/65 | n/a (ordine di grandezza) |
| Recall GRB T90 ≤ 4.096 s ~ 34% | 6/13 | n/a (ordine di grandezza) |
| Numero eventi ~ 100 ± qualche decina | 144 | NON RAGGIUNTO |

## Eventi della pipeline

- Totale: **144**; tier CE: {'R': 105, 'S': 18, 'P': 21}.
- Abbinati al catalogo trigger GBM: 68; a Crupi noti: 70; a Crupi inediti: 21.
- Senza controparte (né GBM né Crupi): **53** (0.43 al giorno su 122 giorni con dati). Non sono "scoperte": vedi `events_without_counterpart.csv`.
- Riferimento paper (fino al 9 luglio): 100 eventi (74 noti, 25 incerti, 1 falso).

## A. Catalogo trigger GBM

- Trigger nel periodo, nei giorni con dati: 143; senza dati validi all'istante del trigger (maschera SAA/buchi): 23; disponibili: 120; rivelati: **68**.
- Con la definizione di docs/WORKING_RULES.md (entro ±150 s da un buco > 500 s): 8 trigger.

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 60 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

GRB del Burst Catalog:

|  | nostro (al 30/06) | paper (al 9/07) |
|---|---|---|
| GRB nel periodo | 93 | 96 |
| senza dati (SAA) | 15 | 15 |
| rivelati / disponibili | 60/78 | 65/81 |
| T90 > 4.096 s | 54/65 | 60/68 (88%) |
| T90 ≤ 4.096 s | 6/13 | 5/13 (34%) |

## B. Tabelle di Crupi

- Noti (Tabella 11, in finestra 71 di 74): ritrovati **70/71 (98.6%)**; per tier: R 62/62 (100.0%), S 3/3 (100.0%), P 5/6 (83.3%).
- Inediti (Tabella 10, in finestra 24 di 25): ritrovati **21/24 (87.5%)**; per tier: R 12/13 (92.3%), S 3/3 (100.0%), P 6/8 (75.0%).

### Noti non ritrovati

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_7 | 2019-03-11 14:23:37 | n8 | GRB190311600 | 3.36 | P | True | 2.82 | 47274.62 | below threshold: max FOCuS r1 within ±60 s = 2.82 sigma |

### Inediti non ritrovati

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_0 | 2019-03-01 09:28:28 | n6 | UNKNOWN: UNC(LP) | 3.63 | P | True | 2.45 | -929.47 | below threshold: max FOCuS r1 within ±60 s = 2.45 sigma |
| 2019_58 | 2019-05-14 07:38:41 | na | UNKNOWN: TGF | 3.09 | P | True | 2.97 | 10307.34 | below threshold: max FOCuS r1 within ±60 s = 2.97 sigma |
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 9.99 | -142.46 | detected but merged: inside our event 122, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

### Significatività: nostro S rispetto a quello di Crupi (eventi abbinati, S di riferimento numerico)

| banda | eventi | mediana S_nostro/S_Crupi | 16° pct | 84° pct |
|---|---|---|---|---|
| r0 | 31 | 1.02 | 0.89 | 1.10 |
| r1 | 33 | 1.03 | 0.95 | 1.15 |
| r2 | 9 | 0.77 | 0.67 | 0.92 |

## Sensibilità alla regola di matching

| margine | GBM rivelati/disponibili | GRB | Crupi noti | Crupi inediti |
|---|---|---|---|---|
| primary (2 bins) | 68/120 | 60/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 10 s | 68/120 | 60/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 60 s | 71/120 | 63/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 1200 s | 73/120 | 64/78 | 70/71 (98.6%) | 22/24 (91.7%) |

## Casi del §1 di docs/WORKING_RULES.md

| tempo (§1) | trigger GBM | trigger_time | rivelato (regola primaria) | evento | inizio evento - trigger [s] | eventi nostri entro ±60 s | in tabelle Crupi |
|---|---|---|---|---|---|---|---|
| 2019-03-08 22:10:12 | GRB190308923 | 2019-03-08 22:09:46.740 | False |  |  | 1 | False |
| 2019-05-25 00:45:54 | GRB190525032 | 2019-05-25 00:45:47.652 | True | 102 | -3.41 | 1 | False |

## Classificazione (Fase 4)

_Tabella classificata assente (`events_classified.csv`): eseguire `python -m benchmark.classify`._

## Limiti noti

- Stabilità rispetto al seed di training non misurata (richiede un nuovo training: da confermare).
- Le feature `fe_wet`/`fe_skw` del classificatore non vengono calcolate (valori costanti); la regola TGF (durata < 0.2 s) non può scattare con bin da 4.096 s.
- Il paper conta fino al 9 luglio; i numeri del paper sono confronti di ordine di grandezza.
