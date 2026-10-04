# Validazione baseline 2019

Generato da `python -m benchmark.validate` il 2026-10-04 12:56 UTC. Tutte le cifre sono calcolate da file su disco.

## Contesto

- Periodo: 2019-03-01 → 2019-06-30 (inclusivo); giorni con dati: 122.
- Run: `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`; motore prodotto dal commit `94f2a2141969dbcc2cd5715cd1411da66ca46455` (codice modificato: False).
- Validazione eseguita dal commit `29c31392eea6fbc34166150fe2d39882c3babd4c`; Python 3.9.23, pandas 1.5.3, numpy 1.26.4.
- Modello: `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1`; seed di training 1 (da `metadata.json` del bundle). Predizioni e trigger riusati da `data/runs/2019-03-01_2019-06-30/engine-v2-seed1` (engine v2, symlink).
- Parametri del motore: soglia 3.0 σ in r1, mu_min 1.2, t_max 50 bin, esclusione SAA ±150 bin, merge 600 s.
- Matching: uno-a-uno; un riferimento è abbinato se il suo istante cade in [inizio evento − 8.192 s, fine evento + 8.192 s]; l'inizio evento è il change point FOCuS (`start_times_offset`).

## Criteri di accettazione (docs/WORKING_RULES.md §6, finestra al 30 giugno)

| criterio | misurato | esito |
|---|---|---|
| Noti di Crupi ritrovati ≥ 90% (≥ 64/71) | 70/71 (98.6%) | OK |
| Tutti gli R e S noti ritrovati (65) | 65/65 (100.0%) | OK |
| Inediti R+S ritrovati ≥ 90% (≥ 15/16) | 15/16 (93.8%) | OK |
| Inediti complessivi ≥ 70% (≥ 17/24) | 21/24 (87.5%) | OK |
| Recall GRB T90 > 4.096 s ~ 88% | 54/65 | n/a (ordine di grandezza) |
| Recall GRB T90 ≤ 4.096 s ~ 34% | 5/13 | n/a (ordine di grandezza) |
| Numero eventi (paper: ~100 fino al 9 luglio) | 136 (per rete, run di questo periodo: `model_03-2019_07-2019_4.4_2026-09-21`: 144; `model_2019-03-01_2019-06-30_seed1`: 136) | informativo: dipende dalla rete |

## Eventi della pipeline

- Totale: **136**; tier CE: {'R': 102, 'S': 11, 'P': 23}.
- Abbinati al catalogo trigger GBM: 67; a Crupi noti: 70; a Crupi inediti: 21.
- Senza controparte (né GBM né Crupi): **46** (0.38 al giorno su 122 giorni con dati). Non sono "scoperte": vedi `events_without_counterpart.csv`.
- Riferimento paper (fino al 9 luglio): 100 eventi (74 noti, 25 incerti, 1 falso).

### Diagnosi per evento degli eventi senza controparte

Distanza dal buco SAA più vicino: minima 680 s, mediana 5212 s. Riferimento di Crupi più vicino entro 1 h: 4/46. Tier: {'R': 29, 'S': 5, 'P': 12}; con il rivelatore nb: 34/46 (contro 49/90 negli eventi abbinati a Crupi).

| trig_ids | start_times | duration | detectors | sigma_C | CE | dist_saa_gap_s | nearest_crupi | nearest_crupi_dt_h | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | l | lat_fermi | predicted_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2019-03-01 06:28:02.424929 | 4.10 | n7 n9 nb | 13.96 | R | 15854.90 | 2019_0 | 3.05 | False | False | False | 1.62 | -25.64 | GRB |
| 3 | 2019-03-06 06:30:21.493791 | 4.10 | n0 n1 n5 | 5.28 | R | 5824.61 | 2019_3 | 0.27 | False | True | False | 1.11 | 2.08 | TGF |
| 6 | 2019-03-07 01:51:23.532494 | 40.96 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 29.11 | R | 15971.32 | 2019_5 | 1.77 | False | False | True | 1.55 | -24.23 | UNC(LP) |
| 8 | 2019-03-08 22:19:41.957523 | 4.55 | n3 | 3.08 | P | 10050.73 | 2019_6 | 35.22 | False | False | False | 1.47 | -25.60 | GRB |
| 9 | 2019-03-09 04:40:38.488395 | 28.67 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 39.22 | R | 4120.65 | 2019_6 | 28.87 | False | False | True | 1.60 | -25.52 | UNC |
| 11 | 2019-03-10 18:58:19.708027 | 12.29 | n5 nb | 6.21 | S | 5189.72 | 2019_6 | -9.42 | True | True | False | 1.11 | -10.85 | GRB |
| 12 | 2019-03-12 03:32:37.160809 | 45.06 | n0 n5 nb | 8.48 | R | 5820.52 | 2019_8 | 7.17 | False | True | False | 1.11 | 2.36 | UNC(LP) |
| 13 | 2019-03-12 03:50:38.522541 | 57.34 | n0 n1 n2 n3 n4 n5 n6 n7 n8 na nb | 62.98 | R | 4882.52 | 2019_8 | 6.91 | False | True | False | 1.53 | -22.44 | UNC(LP) |
| 17 | 2019-03-15 16:13:14.987376 | 379.76 | n5 | 5.39 | P | 5124.18 | 2019_10 | -3.92 | True | True | False | 1.12 | -12.92 | GRB |
| 20 | 2019-03-21 13:16:33.951699 | 310.98 | n5 nb | 8.82 | S | 5144.66 | 2019_13 | 1.43 | True | True | False | 1.12 | -11.62 | GRB |
| 30 | 2019-03-27 10:20:28.621739 | 4.10 | nb | 5.17 | P | 5206.10 | 2019_21 | -3.73 | True | True | False | 1.12 | -10.18 | UNC(LP) |
| 36 | 2019-04-05 13:32:42.186251 | 114.69 | n2 n3 n4 n5 n7 n8 na nb | 23.74 | R | 7057.52 | 2019_27 | 21.25 | False | False | False | 1.65 | 25.50 | GRB |
| 38 | 2019-04-06 13:19:56.038570 | 139.27 | n0 n1 n2 n3 n5 n6 n7 n8 n9 na nb | 31.92 | R | 7000.18 | 2019_27 | -2.54 | False | False | False | 1.65 | 25.32 | GRB |
| 40 | 2019-04-07 04:38:38.490283 | 16.38 | nb | 5.61 | P | 5177.43 | 2019_29 | 9.17 | True | True | False | 1.12 | -11.39 | GRB |
| 44 | 2019-04-08 13:13:33.620110 | 57.34 | n9 nb | 7.15 | R | 5804.13 | 2019_31 | -0.36 | False | True | False | 1.11 | 1.22 | UNC(LP) |
| 45 | 2019-04-09 10:15:12.665876 | 94.21 | n0 n1 n2 n6 n9 na nb | 33.47 | R | 10059.94 | 2019_31 | -21.36 | False | False | False | 1.61 | -25.47 | UNC(LP) |
| 46 | 2019-04-10 08:26:24.577345 | 4.10 | n1 n9 na nb | 31.62 | R | 15802.63 | 2019_32 | 25.38 | False | False | False | 1.60 | -25.57 | TGF |
| 49 | 2019-04-12 00:39:53.566327 | 4.10 | n2 | 3.21 | P | 692.24 | 2019_33 | -10.77 | False | False | False | 1.06 | 18.87 | GRB |
| 50 | 2019-04-13 01:41:57.004926 | 8.19 | nb | 5.08 | P | 5193.82 | 2019_33 | -35.79 | True | True | False | 1.11 | -10.56 | GRB |
| 51 | 2019-04-14 10:16:07.497527 | 57.35 | n2 n9 na nb | 7.18 | R | 5808.24 | 2019_34 | 17.90 | False | True | False | 1.11 | 1.64 | UNC(LP) |
| 53 | 2019-04-17 22:57:08.272410 | 333.53 | nb | 3.99 | P | 5144.68 | 2019_35 | 34.98 | True | True | False | 1.12 | -12.21 | GRB |
| 59 | 2019-04-22 18:58:31.100524 | 4.10 | n0 n2 n9 na | 6.96 | R | 679.95 | 2019_39 | -2.89 | False | False | False | 1.09 | 18.42 | UNC |
| 61 | 2019-04-23 20:00:02.635642 | 286.19 | nb | 6.68 | P | 5169.26 | 2019_41 | -21.06 | True | True | False | 1.12 | -11.19 | GRB |
| 62 | 2019-04-25 04:51:44.183935 | 12.29 | n2 n3 n4 n5 n6 n7 n8 na nb | 60.32 | R | 4980.84 | 2019_41 | -53.87 | False | True | False | 1.50 | -21.27 | UNC(LP) |
| 65 | 2019-04-29 17:03:41.331763 | 4.10 | n5 | 4.51 | P | 5218.39 | 2019_44 | 0.78 | True | True | False | 1.12 | -10.37 | GRB |
| 67 | 2019-05-01 01:37:51.180214 | 57.34 | n3 n4 n5 n6 n8 n9 nb | 10.84 | R | 5812.32 | 2019_45 | 26.41 | False | True | False | 1.11 | 1.99 | TGF |
| 73 | 2019-05-06 22:40:19.207866 | 147.46 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 24.46 | R | 5837.09 | 2019_49 | -4.86 | False | True | False | 1.12 | 1.29 | UNC(LP) |
| 83 | 2019-05-14 11:57:51.300410 | 69.63 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 96.53 | R | 10547.37 | 2019_60 | 0.09 | False | False | False | 1.14 | -15.82 | GF |
| 87 | 2019-05-15 08:36:45.387608 | 414.67 | n6 n8 | 6.13 | S | 5091.41 | 2019_63 | 7.47 | True | True | False | 1.12 | -13.40 | GRB |
| 91 | 2019-05-19 14:34:51.884471 | 36.86 | n2 n4 n5 n6 n7 n8 na nb | 14.94 | R | 7045.23 | 2019_65 | -7.16 | False | False | False | 1.66 | 25.44 | GRB |
| 93 | 2019-05-20 12:41:05.052515 | 49.15 | n4 n7 n8 na nb | 12.76 | R | 13037.56 | 2019_67 | 1.67 | False | False | False | 1.61 | 24.21 | GRB |
| 95 | 2019-05-21 05:39:42.484606 | 358.33 | n0 n5 n6 n9 nb | 13.40 | S | 5115.98 | 2019_67 | -15.30 | True | True | False | 1.12 | -12.33 | GRB |
| 96 | 2019-05-22 15:28:38.574776 | 4.10 | na | 3.05 | P | 1380.37 | 2019_68 | 43.79 | False | False | False | 1.40 | 25.47 | GRB |
| 98 | 2019-05-27 02:42:44.068605 | 289.26 | n8 n9 na nb | 12.68 | R | 5161.06 | 2019_69 | 44.84 | True | True | False | 1.12 | -11.23 | GRB |
| 100 | 2019-05-29 09:57:11.244783 | 12.29 | n9 na nb | 40.40 | R | 4292.70 | 2019_69 | -10.35 | False | False | False | 1.59 | -25.05 | TGF |
| 101 | 2019-05-29 10:42:51.525655 | 274.44 | n0 n1 n3 n4 n5 n6 n7 n9 na nb | 84.99 | R | 1552.41 | 2019_69 | -11.11 | False | False | False | 1.53 | 25.48 | UNC(LP) |
| 105 | 2019-06-03 08:20:31.645232 | 8.19 | n0 n5 | 4.09 | R | 5812.35 | 2019_73 | 10.74 | False | True | False | 1.11 | 2.69 | UNC(LP) |
| 111 | 2019-06-06 21:01:29.214995 | 4.10 | nb | 4.01 | P | 5156.97 | 2019_78 | 4.69 | True | True | False | 1.12 | -12.19 | GRB |
| 114 | 2019-06-08 05:36:49.079595 | 28.67 | n3 n4 n5 | 6.13 | R | 5816.44 | 2019_79 | -5.39 | False | True | False | 1.11 | 2.63 | UNC(LP) |
| 116 | 2019-06-09 02:40:06.101176 | 4.10 | n6 n7 n8 n9 nb | 41.16 | R | 10092.76 | 2019_83 | 4.95 | False | False | False | 1.60 | -25.45 | TGF |
| 121 | 2019-06-12 18:04:34.984655 | 269.81 | n5 nb | 6.81 | S | 5193.83 | 2019_87 | 10.05 | True | True | False | 1.12 | -11.16 | GRB |
| 124 | 2019-06-14 02:38:51.553282 | 61.44 | n3 n5 nb | 6.86 | R | 5828.72 | 2019_88 | -15.86 | False | True | False | 1.11 | 1.86 | TGF |
| 126 | 2019-06-18 15:06:55.681582 | 258.40 | n2 n3 n4 n5 n8 | 14.13 | R | 5156.94 | 2019_90 | 9.30 | True | True | False | 1.12 | -9.93 | UNC(LP) |
| 130 | 2019-06-24 12:10:09.324833 | 4.10 | n1 | 3.52 | P | 5218.39 | 2019_93 | 41.94 | True | True | False | 1.11 | -10.67 | GRB |
| 134 | 2019-06-29 09:25:03.388667 | 319.13 | n0 n1 n5 n9 nb | 11.95 | R | 5144.66 | 2019_95 | -20.90 | True | True | False | 1.12 | -11.29 | UNC |
| 135 | 2019-06-30 18:01:05.792527 | 4.10 | n6 nb | 5.68 | R | 5824.61 | 2019_96 | 45.88 | False | True | False | 1.11 | 1.92 | UNC(LP) |

### Flag di post-processing (non cambiano l'elenco degli eventi)

`saa_edge_short_passage`: inizio evento (change point) entro 200 s prima dell'entrata o dopo l'uscita di un passaggio SAA il cui buco nei dati è ≤ 500 s, quindi non mascherato. `saa_region_proximity`: Fermi entro 3.5° dalla regione con flag SAA nelle POSHIST. `near_zero_prediction`: i bin dell'evento, estesi di 5 per lato, toccano un bin con fondo previsto ≤ 0 (6 bin in questa run: eventi 6, 9). Definizioni in `models/saa_flags.py` e `docs/ORBIT_ANALYSIS.md`; per evento in `events_flags.csv`.

| eventi | n | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | almeno uno |
|---|---|---|---|---|---|
| abbinati Crupi/GBM | 90 | 0 | 1 | 0 | 1 |
| senza controparte | 46 | 17 | 29 | 2 | 31 |
| tutti | 136 | 17 | 30 | 2 | 32 |

## A. Catalogo trigger GBM

- Trigger nel periodo, nei giorni con dati: 143; senza dati validi all'istante del trigger (maschera SAA/buchi): 23; disponibili: 120; rivelati: **67**.
- Con la definizione di docs/WORKING_RULES.md (entro ±150 s da un buco > 500 s): 8 trigger.

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 59 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

GRB del Burst Catalog:

|  | nostro (al 30/06) | paper (al 9/07) |
|---|---|---|
| GRB nel periodo | 93 | 96 |
| senza dati (SAA) | 15 | 15 |
| rivelati / disponibili | 59/78 | 65/81 |
| T90 > 4.096 s | 54/65 | 60/68 (88%) |
| T90 ≤ 4.096 s | 5/13 | 5/13 (34%) |

## B. Tabelle di Crupi

- Noti (Tabella 11, in finestra 71 di 74): ritrovati **70/71 (98.6%)**; per tier: R 62/62 (100.0%), S 3/3 (100.0%), P 5/6 (83.3%).
- Inediti (Tabella 10, in finestra 24 di 25): ritrovati **21/24 (87.5%)**; per tier: R 12/13 (92.3%), S 3/3 (100.0%), P 6/8 (75.0%).

### Noti non ritrovati

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_7 | 2019-03-11 14:23:37 | n8 | GRB190311600 | 3.36 | P | True | 2.96 | 47299.20 | below threshold: max FOCuS r1 within ±60 s = 2.96 sigma |

### Inediti non ritrovati

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_0 | 2019-03-01 09:28:28 | n6 | UNKNOWN: UNC(LP) | 3.63 | P | True | 1.65 | -10968.94 | below threshold: max FOCuS r1 within ±60 s = 1.65 sigma |
| 2019_58 | 2019-05-14 07:38:41 | na | UNKNOWN: TGF | 3.09 | P | True | 2.87 | 10307.34 | below threshold: max FOCuS r1 within ±60 s = 2.87 sigma |
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 10.09 | -228.48 | detected but merged: inside our event 115, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

### Significatività: nostro S rispetto a quello di Crupi (eventi abbinati, S di riferimento numerico)

| banda | eventi | mediana S_nostro/S_Crupi | 16° pct | 84° pct |
|---|---|---|---|---|
| r0 | 30 | 1.00 | 0.92 | 1.07 |
| r1 | 33 | 1.01 | 0.90 | 1.06 |
| r2 | 10 | 0.74 | 0.64 | 1.10 |

## Sensibilità alla regola di matching

| margine | GBM rivelati/disponibili | GRB | Crupi noti | Crupi inediti |
|---|---|---|---|---|
| primary (2 bins) | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 10 s | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 60 s | 69/120 | 61/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 1200 s | 72/120 | 63/78 | 70/71 (98.6%) | 21/24 (87.5%) |

## Casi del §1 di docs/WORKING_RULES.md

| tempo (§1) | trigger GBM | trigger_time | rivelato (regola primaria) | evento | inizio evento - trigger [s] | eventi nostri entro ±60 s | in tabelle Crupi |
|---|---|---|---|---|---|---|---|
| 2019-03-08 22:10:12 | GRB190308923 | 2019-03-08 22:09:46.740 | False |  |  | 0 | False |
| 2019-05-25 00:45:54 | GRB190525032 | 2019-05-25 00:45:47.652 | False |  |  | 0 | False |

## Classificazione (Fase 4)

Il classificatore è la **baseline euristica** di Crupi, da superare con un modello appreso (XGBoost, fase successiva). Le regole vengono dalla "manual classification logic" di `pipeline/script_classification2.py` (upstream, 2023): soglie lette da decision tree uno-contro-resto (profondità 3) e rifinite a mano sul catalogo etichettato 2010-11, 2014, 2019; le random forest servivano allo studio delle feature, non come classificatore finale.

Differenze rispetto alle regole originali: mancano la regola FP e le feature `fe_*` della curva di luce (calcolate con `tsfel` nel branch upstream `ric_review_28062023`), quindi i termini `fe_wet > 2.054` (GRB) e `fe_skw <= 0.345` (UNC(LP)) sono neutri. Le regole sono valutate solo sugli eventi abbinati a Crupi (gli eventi senza controparte non hanno una classe di riferimento).

### Per regola, uno-contro-resto (come nello script di Crupi) — 91 eventi abbinati

| regola | positivi Crupi | flag regola | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|
| GRB | 74 | 79 | 72 | 7 | 2 | 0.91 | 0.97 |
| SF | 6 | 6 | 5 | 1 | 1 | 0.83 | 0.83 |
| TGF | 3 | 4 | 1 | 3 | 2 | 0.25 | 0.33 |
| UNC(LP) | 10 | 15 | 8 | 7 | 2 | 0.53 | 0.80 |
| GF | 2 | 17 | 0 | 17 | 2 | 0.00 | 0.00 |

### Etichetta singola (nostra convenzione di priorità: GRB, TGF, SF, UNC(LP), GF, UNC)

Classe predetta tra quelle tentative di Crupi: 79/91 (86.8%).

Matrice di confusione sugli eventi con classe Crupi univoca (87):

```
predetta  GRB  SF  TGF  UNC  UNC(LP)
Crupi                               
GRB        68   0    0    1        1
SF          0   4    1    0        0
TGF         2   0    0    0        0
UNC         0   0    0    0        0
UNC(LP)     5   1    0    1        3
```

Leakage: `tests/test_classifier.py::test_catalog_does_not_change_prediction` verifica che le colonne del catalogo non cambino la classe; `TestRulesMatchCrupi` verifica che i flag coincidano con la trascrizione delle regole di Crupi.

## Limiti noti

- Stabilità rispetto alla rete (stesso codice, addestramento diverso): con la rete `model_03-2019_07-2019_4.4_2026-09-21` (run `engine-v2`, 144 eventi): 126 coppie, 10 eventi solo qui, 18 solo là. Gli eventi forti e quelli abbinati a Crupi/GBM sono stabili; cambiano soprattutto quelli senza controparte (vedi `docs/ORBIT_ANALYSIS.md`).
- Passaggi SAA brevi non mascherati: 45 passaggi nel periodo hanno un buco nei dati ≤ 500 s, quindi non coperto dalla maschera (che agisce solo sui buchi > 500 s); la rete sottostima il fondo nell'avvicinamento. Eventi con `saa_edge_short_passage` in questa run: 17 (17 senza controparte; gruppo A di ORBIT_ANALYSIS).
- Bordo settentrionale della SAA: eventi senza controparte entro 3.5° dalla regione SAA ma non al bordo di un passaggio breve: 12 (comprende il gruppo B di ORBIT_ANALYSIS).
- Fondo previsto ≤ 0: 212 celle (6 bin) con fondo previsto ≤ 0 in questa run. Da engine v3 quei bin sono esclusi dal calcolo di S, ma il trigger che parte accanto resta; eventi adiacenti a questi bin vanno considerati sospetti.
- Classificatore: mancano la regola FP e le feature `fe_*` (tsfel, branch upstream `ric_review_28062023`): i termini che le usano sono neutri.
- Il paper conta fino al 9 luglio; i numeri del paper sono confronti di ordine di grandezza.
