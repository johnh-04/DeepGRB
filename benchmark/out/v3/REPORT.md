# Validazione baseline 2019

Generato da `python -m benchmark.validate` il 2026-10-04 12:57 UTC. Tutte le cifre sono calcolate da file su disco.

## Contesto

- Periodo: 2019-03-01 → 2019-06-30 (inclusivo); giorni con dati: 122.
- Run: `data/runs/2019-03-01_2019-06-30/engine-v3`; motore prodotto dal commit `94f2a2141969dbcc2cd5715cd1411da66ca46455` (codice modificato: False).
- Validazione eseguita dal commit `29c31392eea6fbc34166150fe2d39882c3babd4c`; Python 3.9.23, pandas 1.5.3, numpy 1.26.4.
- Modello: `data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21`; modello legacy addestrato il 2026-09-21 da codice equivalente a upstream: seed non registrato. Predizioni e trigger riusati da `data/runs/2019-03-01_2019-06-30/engine-v2` (engine v2, symlink).
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
| Recall GRB T90 ≤ 4.096 s ~ 34% | 6/13 | n/a (ordine di grandezza) |
| Numero eventi (paper: ~100 fino al 9 luglio) | 144 (per rete, run di questo periodo: `model_03-2019_07-2019_4.4_2026-09-21`: 144; `model_2019-03-01_2019-06-30_seed1`: 136) | informativo: dipende dalla rete |

## Eventi della pipeline

- Totale: **144**; tier CE: {'R': 105, 'S': 18, 'P': 21}.
- Abbinati al catalogo trigger GBM: 68; a Crupi noti: 70; a Crupi inediti: 21.
- Senza controparte (né GBM né Crupi): **53** (0.43 al giorno su 122 giorni con dati). Non sono "scoperte": vedi `events_without_counterpart.csv`.
- Riferimento paper (fino al 9 luglio): 100 eventi (74 noti, 25 incerti, 1 falso).

### Diagnosi per evento degli eventi senza controparte

Distanza dal buco SAA più vicino: minima 672 s, mediana 5218 s. Riferimento di Crupi più vicino entro 1 h: 6/53. Tier: {'R': 31, 'S': 12, 'P': 10}; con il rivelatore nb: 45/53 (contro 49/90 negli eventi abbinati a Crupi).

| trig_ids | start_times | duration | detectors | sigma_C | CE | dist_saa_gap_s | nearest_crupi | nearest_crupi_dt_h | saa_edge_short_passage | saa_region_proximity | near_zero_prediction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2019-03-01 09:13:39.495612 | 81.92 | n0 n1 n2 n3 n4 n5 n6 n8 n9 na nb | 13.70 | R | 5815.43 | 2019_0 | 0.26 | False | True | False |
| 3 | 2019-03-06 06:39:26.270521 | 172.03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 86.47 | R | 5361.76 | 2019_3 | 0.14 | False | True | False |
| 7 | 2019-03-08 22:10:12.148650 | 8.19 | n9 nb | 4.41 | S | 9481.38 | 2019_6 | 35.37 | False | False | False |
| 8 | 2019-03-09 04:27:32.043872 | 8.19 | n2 n3 n7 n8 | 18.19 | R | 4964.44 | 2019_6 | 29.10 | False | False | False |
| 10 | 2019-03-10 18:58:19.708027 | 12.29 | n5 nb | 6.47 | S | 5189.72 | 2019_6 | -9.42 | True | True | False |
| 11 | 2019-03-12 03:32:33.064740 | 57.34 | n0 n3 n5 n6 n8 n9 na nb | 11.29 | R | 5845.09 | 2019_8 | 7.18 | False | True | False |
| 12 | 2019-03-12 03:49:45.273712 | 135.17 | n0 n1 n2 n3 n4 n5 n6 n7 n8 na nb | 73.74 | R | 4919.38 | 2019_8 | 6.92 | False | True | False |
| 16 | 2019-03-15 16:13:14.987376 | 379.76 | n0 n1 n3 n5 nb | 10.17 | S | 5111.89 | 2019_10 | -3.92 | True | True | False |
| 19 | 2019-03-21 13:16:33.951699 | 306.89 | n5 nb | 8.12 | S | 5144.66 | 2019_13 | 1.43 | True | True | False |
| 26 | 2019-03-26 10:31:48.816601 | 427.17 | nb | 5.07 | P | 5087.32 | 2019_18 | -10.54 | True | True | False |
| 30 | 2019-03-27 10:19:39.468979 | 238.87 | nb | 6.61 | P | 5193.81 | 2019_21 | -3.72 | True | True | False |
| 33 | 2019-04-01 07:35:23.484790 | 4.10 | n6 nb | 6.68 | S | 5132.37 | 2019_23 | -4.24 | True | True | False |
| 37 | 2019-04-05 13:32:50.378372 | 77.83 | n2 n3 n4 n5 n7 na | 17.81 | R | 7045.24 | 2019_27 | 21.24 | False | False | False |
| 39 | 2019-04-06 13:19:51.942503 | 114.69 | n0 n1 n2 n3 n5 n6 n7 n8 n9 nb | 29.54 | R | 7000.18 | 2019_27 | -2.54 | False | False | False |
| 41 | 2019-04-07 04:38:26.202073 | 28.67 | nb | 5.98 | P | 5177.43 | 2019_29 | 9.17 | True | True | False |
| 45 | 2019-04-08 13:13:21.331919 | 122.88 | n0 n1 n5 n6 n9 nb | 9.84 | R | 5816.41 | 2019_31 | -0.36 | False | True | False |
| 46 | 2019-04-09 10:15:12.665876 | 126.98 | n0 n1 n2 n6 n9 na | 38.60 | R | 10051.75 | 2019_31 | -21.37 | False | False | False |
| 47 | 2019-04-10 08:26:20.481275 | 8.19 | n1 n9 na nb | 31.06 | R | 15806.73 | 2019_32 | 25.38 | False | False | False |
| 50 | 2019-04-12 01:53:33.220988 | 16.38 | nb | 5.56 | P | 5075.03 | 2019_33 | -11.98 | True | True | False |
| 51 | 2019-04-13 01:41:36.524514 | 217.75 | n8 n9 nb | 10.56 | S | 5193.82 | 2019_33 | -35.79 | True | True | False |
| 52 | 2019-04-14 10:16:07.497527 | 61.44 | n2 n7 n8 n9 na nb | 8.15 | R | 5824.63 | 2019_34 | 17.91 | False | True | False |
| 54 | 2019-04-17 22:57:04.176326 | 337.63 | n5 n7 nb | 8.78 | R | 5111.91 | 2019_35 | 34.99 | True | True | False |
| 60 | 2019-04-22 18:58:31.100524 | 4.10 | n0 n2 n4 n9 na | 7.62 | R | 671.76 | 2019_39 | -2.89 | False | False | False |
| 62 | 2019-04-23 19:59:50.347401 | 302.57 | n2 n4 n5 n6 n8 na nb | 16.57 | R | 5140.58 | 2019_41 | -21.05 | True | True | False |
| 65 | 2019-04-29 17:03:41.331763 | 197.94 | n5 | 4.46 | P | 5218.39 | 2019_44 | 0.78 | True | True | False |
| 67 | 2019-05-01 01:37:55.276282 | 53.25 | n3 n4 n5 n6 n8 n9 nb | 11.05 | R | 5812.32 | 2019_45 | 26.41 | False | True | False |
| 73 | 2019-05-06 22:40:19.207866 | 139.27 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 26.26 | R | 5837.09 | 2019_49 | -4.86 | False | True | False |
| 83 | 2019-05-14 11:57:51.300410 | 73.73 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 98.45 | R | 10547.37 | 2019_60 | 0.09 | False | False | False |
| 85 | 2019-05-14 13:44:33.450626 | 12.29 | n0 n2 n3 n4 n5 n6 n7 n8 n9 na nb | 40.58 | R | 17092.88 | 2019_61 | 0.04 | False | False | False |
| 88 | 2019-05-15 08:36:45.387608 | 414.67 | n6 n8 | 6.91 | S | 5091.41 | 2019_63 | 7.47 | True | True | False |
| 90 | 2019-05-16 08:25:12.675210 | 12.29 | n6 nb | 6.23 | S | 5222.48 | 2019_63 | -16.34 | True | True | False |
| 91 | 2019-05-17 16:59:06.017297 | 65.54 | n6 n8 n9 na nb | 8.97 | R | 5808.22 | 2019_64 | 2.53 | False | True | False |
| 94 | 2019-05-19 14:35:00.076604 | 32.77 | n2 n4 n5 n6 n7 n8 na nb | 14.55 | R | 7045.23 | 2019_65 | -7.16 | False | False | False |
| 96 | 2019-05-20 12:41:05.052515 | 61.44 | n3 n4 n7 n8 na nb | 15.46 | R | 13037.56 | 2019_67 | 1.67 | False | False | False |
| 98 | 2019-05-21 05:39:46.580671 | 354.24 | n0 n5 n6 n8 n9 nb | 14.08 | R | 5132.37 | 2019_67 | -15.31 | True | True | False |
| 99 | 2019-05-22 05:28:21.880913 | 4.10 | nb | 3.11 | P | 5275.73 | 2019_67 | -39.12 | False | True | False |
| 100 | 2019-05-22 14:15:48.071600 | 8.19 | nb | 4.71 | P | 5808.22 | 2019_68 | 45.02 | False | True | False |
| 103 | 2019-05-26 02:54:40.566926 | 20.48 | n9 nb | 5.54 | S | 5066.84 | 2019_68 | -39.64 | True | True | False |
| 104 | 2019-05-27 02:42:15.396011 | 322.03 | n5 n6 n7 n8 n9 na nb | 21.08 | R | 5124.19 | 2019_69 | 44.85 | True | True | False |
| 105 | 2019-05-28 11:18:20.789026 | 4.10 | nb | 4.67 | P | 5795.96 | 2019_69 | 12.26 | False | True | False |
| 107 | 2019-05-29 09:57:11.244783 | 8.19 | n9 na nb | 40.30 | R | 4292.70 | 2019_69 | -10.35 | False | False | False |
| 108 | 2019-05-29 10:42:51.525655 | 294.92 | n0 n1 n3 n4 n5 n6 n9 na nb | 77.47 | R | 1552.41 | 2019_69 | -11.11 | False | False | False |
| 112 | 2019-06-01 23:46:14.423396 | 195.82 | nb | 6.25 | P | 5226.61 | 2019_72 | -27.60 | True | True | False |
| 114 | 2019-06-04 04:28:09.810622 | 8.19 | n6 | 3.13 | P | 13164.83 | 2019_74 | 6.24 | False | False | False |
| 119 | 2019-06-06 21:01:21.022813 | 12.29 | n6 nb | 4.82 | R | 5132.40 | 2019_78 | 4.70 | True | True | False |
| 123 | 2019-06-09 02:40:06.101176 | 4.10 | n6 n7 n8 n9 nb | 41.02 | R | 10092.76 | 2019_83 | 4.95 | False | False | False |
| 128 | 2019-06-12 18:03:54.023883 | 314.87 | n3 n4 n5 nb | 12.55 | S | 5152.87 | 2019_87 | 10.06 | True | True | False |
| 131 | 2019-06-14 02:39:32.514097 | 4.10 | n5 n6 nb | 6.00 | R | 5820.53 | 2019_88 | -15.86 | False | True | False |
| 133 | 2019-06-18 15:07:03.873696 | 246.12 | n2 n3 n4 n5 n6 n8 nb | 17.54 | R | 5128.27 | 2019_90 | 9.31 | True | True | False |
| 137 | 2019-06-23 12:22:24.004204 | 357.47 | n2 n3 n5 n6 nb | 9.73 | S | 5133.20 | 2019_93 | 65.74 | True | True | False |
| 138 | 2019-06-24 12:10:09.324833 | 53.25 | n1 n2 | 7.35 | S | 5218.39 | 2019_93 | 41.94 | True | True | False |
| 142 | 2019-06-29 09:25:03.388667 | 319.13 | n0 n6 n8 n9 nb | 13.51 | R | 5144.66 | 2019_95 | -20.90 | True | True | False |
| 143 | 2019-06-30 18:00:57.600395 | 16.38 | n6 nb | 6.65 | R | 5828.70 | 2019_96 | 45.88 | False | True | False |

### Flag di post-processing (non cambiano l'elenco degli eventi)

`saa_edge_short_passage`: inizio evento (change point) entro 200 s prima dell'entrata o dopo l'uscita di un passaggio SAA il cui buco nei dati è ≤ 500 s, quindi non mascherato. `saa_region_proximity`: Fermi entro 3.5° dalla regione con flag SAA nelle POSHIST. `near_zero_prediction`: i bin dell'evento, estesi di 5 per lato, toccano un bin con fondo previsto ≤ 0 (0 bin in questa run). Definizioni in `models/saa_flags.py` e `docs/ORBIT_ANALYSIS.md`; per evento in `events_flags.csv`.

| eventi | n | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | almeno uno |
|---|---|---|---|---|---|
| abbinati Crupi/GBM | 91 | 0 | 1 | 0 | 1 |
| senza controparte | 53 | 24 | 38 | 0 | 38 |
| tutti | 144 | 24 | 39 | 0 | 39 |

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
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 9.99 | -228.48 | detected but merged: inside our event 122, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

### Significatività: nostro S rispetto a quello di Crupi (eventi abbinati, S di riferimento numerico)

| banda | eventi | mediana S_nostro/S_Crupi | 16° pct | 84° pct |
|---|---|---|---|---|
| r0 | 31 | 1.02 | 0.89 | 1.10 |
| r1 | 33 | 1.03 | 0.95 | 1.15 |
| r2 | 9 | 0.76 | 0.67 | 0.92 |

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

Il classificatore è la **baseline euristica** di Crupi, da superare con un modello appreso (XGBoost, fase successiva). Le regole vengono dalla "manual classification logic" di `pipeline/script_classification2.py` (upstream, 2023): soglie lette da decision tree uno-contro-resto (profondità 3) e rifinite a mano sul catalogo etichettato 2010-11, 2014, 2019; le random forest servivano allo studio delle feature, non come classificatore finale.

Differenze rispetto alle regole originali: mancano la regola FP e le feature `fe_*` della curva di luce (calcolate con `tsfel` nel branch upstream `ric_review_28062023`), quindi i termini `fe_wet > 2.054` (GRB) e `fe_skw <= 0.345` (UNC(LP)) sono neutri. Le regole sono valutate solo sugli eventi abbinati a Crupi (gli eventi senza controparte non hanno una classe di riferimento).

_Tabella classificata assente (`events_classified.csv`): eseguire `python -m benchmark.classify`._

## Limiti noti

- Stabilità rispetto alla rete (stesso codice, addestramento diverso): con la rete `model_2019-03-01_2019-06-30_seed1` (run `engine-v2-seed1`, 136 eventi): 126 coppie, 18 eventi solo qui, 10 solo là. Gli eventi forti e quelli abbinati a Crupi/GBM sono stabili; cambiano soprattutto quelli senza controparte (vedi `docs/ORBIT_ANALYSIS.md`).
- Passaggi SAA brevi non mascherati: 45 passaggi nel periodo hanno un buco nei dati ≤ 500 s, quindi non coperto dalla maschera (che agisce solo sui buchi > 500 s); la rete sottostima il fondo nell'avvicinamento. Eventi con `saa_edge_short_passage` in questa run: 24 (24 senza controparte; gruppo A di ORBIT_ANALYSIS).
- Bordo settentrionale della SAA: eventi senza controparte entro 3.5° dalla regione SAA ma non al bordo di un passaggio breve: 14 (comprende il gruppo B di ORBIT_ANALYSIS).
- Fondo previsto ≤ 0: 0 celle (0 bin) con fondo previsto ≤ 0 in questa run. Da engine v3 quei bin sono esclusi dal calcolo di S, ma il trigger che parte accanto resta; eventi adiacenti a questi bin vanno considerati sospetti.
- Classificatore: mancano la regola FP e le feature `fe_*` (tsfel, branch upstream `ric_review_28062023`): i termini che le usano sono neutri.
- Il paper conta fino al 9 luglio; i numeri del paper sono confronti di ordine di grandezza.
