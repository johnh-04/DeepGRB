# Results of the run `engine-v3-seed1` (2019-03-01 → 2019-06-30)

Written by `validation/report.py` (step 9 of `pipeline/pipeline_bkg.py`); validation of 2026-10-05 19:51 UTC, commit `5a3f68b460`. Every number is read from the files of the run; the full tables are in `validation/` and `results/`.

## 1. Run, network and parameters

- Period: **2019-03-01 → 2019-06-30** (UTC days, both included); run `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`.
- Engine: v3; executions: 2026-10-04 16:51 commit `21e4db1703` (steps to run at start: 3, 4, 5, 6, 7, 8, 9); 2026-10-04 17:03 commit `21e4db1703` (steps to run at start: 9).
- Network: bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1`; training seed 1; bundle sha256 `0eae86f65d97b285976955b98d80a8b5df8202fb8ea9df84973958eb7bc9ee08`.
- Predictions (step 3) and FOCuS outputs (step 4) computed with the same bundle by engine v2, whose steps 3-4 are unchanged; linked from `data/runs/2019-03-01_2019-06-30/engine-v2-seed1` (symlink).
- Training: 64 epochs (best 57), 2048 units, lr 0.0008, batch 2048, 378.0 s on /physical_device:GPU:0.
- Parameters: bin 4.096 s; FOCuS mu_min 1.2, t_max 50 bins (input: rates (counts/s)); threshold 3.0 σ in r1 on ≥ 1 detector(s); merge 600 s; SAA mask ±150 bins around data gaps > 500.0 s.

## 2. Events

- Total: **136**; CE tiers: R 102, S 11, P 23 (R: several detectors and several energy ranges; S: several detectors, one range; P: the others).
- Matched to the GBM trigger catalog: 67; to Crupi's known events: 70; to Crupi's unknown events: 21. Without counterpart: **46** (0.38 per day over 122 days with data).

## 3. Official Fermi-GBM catalog

Primary rule: one-to-one matching, trigger time within [event start − 8.192 s, event end + 8.192 s].

- Triggers in the period, on days with data: 143; without valid data at the trigger time (SAA mask or gap): 23; available: 120; detected: **67**.
- Within ±150 s of a data gap > 500 s: 8 triggers.

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 59 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

GRBs of the Burst Catalog (T90):

|  | this run | paper (to 2019-07-09) |
|---|---|---|
| GRBs in the period | 93 | 96 |
| without data (SAA) | 15 | 15 |
| detected / available | 59/78 (75.6%) | 65/81 |
| T90 > 4.096 s | 54/65 (83.1%) | 60/68 (88%) |
| T90 ≤ 4.096 s | 5/13 (38.5%) | 5/13 (34%) |

Sensitivity to the matching window:

| margin | GBM detected/available | GRB | Crupi known | Crupi unknown |
|---|---|---|---|---|
| primary (2 bins) | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 10 s | 67/120 | 59/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 60 s | 69/120 | 61/78 | 70/71 (98.6%) | 21/24 (87.5%) |
| 1200 s | 72/120 | 63/78 | 70/71 (98.6%) | 21/24 (87.5%) |

## 4. Comparison with Crupi et al. (2023)

| criterion (docs/VALIDATION.md) | measured | result |
|---|---|---|
| Crupi's known events found ≥ 90% | 70/71 (98.6%) | ✔ |
| All known R and S events found | 65/65 (100.0%) | ✔ |
| Unknown R+S events found ≥ 90% | 15/16 (93.8%) | ✔ |
| All unknown events found ≥ 70% | 21/24 (87.5%) | ✔ |
| GRB recall T90 > 4.096 s ~ 88% (paper) | 54/65 (83.1%) | order of magnitude |
| GRB recall T90 ≤ 4.096 s ~ 34% (paper) | 5/13 (38.5%) | order of magnitude |
| Number of events ~ 100 (paper, to 2019-07-09) | 136 | informative: depends on the network |

- Known events (Table 11; 71 of 74 in the period): found **70/71 (98.6%)**; by tier: R 62/62, S 3/3, P 5/6.
- Unknown events (Table 10; 24 of 25 in the period): found **21/24 (87.5%)**; by tier: R 12/13, S 3/3, P 6/8.

Known events not found:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_7 | 2019-03-11 14:23:37 | n8 | GRB190311600 | 3.36 | P | True | 2.96 | 47299.20 | below threshold: max FOCuS r1 within ±60 s = 2.96 sigma |

Unknown events not found:

| id | trigger_time_utc | detectors | catalog_name | S_r1 | CE | has_data | focus_r1_max_pm60s | nearest_event_dt_s | diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| 2019_0 | 2019-03-01 09:28:28 | n6 | UNKNOWN: UNC(LP) | 3.63 | P | True | 1.65 | -10968.94 | below threshold: max FOCuS r1 within ±60 s = 1.65 sigma |
| 2019_58 | 2019-05-14 07:38:41 | na | UNKNOWN: TGF | 3.09 | P | True | 2.87 | 10307.34 | below threshold: max FOCuS r1 within ±60 s = 2.87 sigma |
| 2019_81 | 2019-06-08 20:23:03 | n0 n1 n2 n3 n4 n5 n6 n7 n8 n9 na nb | UNKNOWN: UNC(LP) | >10 | R | True | 10.09 | -228.48 | detected but merged: inside our event 115, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |

Significance, our S against Crupi's (matched events with a numeric reference S):

| range | events | median S_ours/S_Crupi | 16th pct | 84th pct |
|---|---|---|---|---|
| r0 | 30 | 1.00 | 0.92 | 1.07 |
| r1 | 33 | 1.01 | 0.90 | 1.06 |
| r2 | 10 | 0.74 | 0.64 | 1.10 |

## 5. Events without counterpart and post-processing flags

Events without counterpart (neither the GBM catalog nor Crupi's tables) are **not discoveries**: they are candidates to be checked. The flags add columns and never change the event list (definitions in `models/flags.py`): `saa_edge_short_passage` (start within 200 s of an SAA passage whose data gap is not masked), `saa_region_proximity` (Fermi within 3.5° of the SAA region), `near_zero_prediction` (event ±5 bins touching a bin with predicted background ≤ 0).

| events | n | saa_edge_short_passage | saa_region_proximity | near_zero_prediction | at least one |
|---|---|---|---|---|---|
| matched to Crupi/GBM | 90 | 0 | 1 | 0 | 1 |
| without counterpart | 46 | 17 | 29 | 2 | 31 |
| all | 136 | 17 | 30 | 2 | 32 |

Events without counterpart (46) by combination of flags:

| flags | events |
|---|---|
| saa_edge_short_passage, saa_region_proximity | 17 |
| none | 15 |
| saa_region_proximity | 12 |
| near_zero_prediction | 2 |

Tiers: R 29, S 5, P 12; distance from the nearest SAA gap: minimum 680 s, median 5212 s. Full list: `validation/events_without_counterpart.csv`.

## 6. Classification (Crupi's heuristic baseline)

Rules of Crupi's "manual classification logic" (upstream `pipeline/script_classification2.py`): thresholds read from one-vs-rest decision trees and refined by hand. A deliberately simple baseline, to be outperformed by a learned classifier. The FP rule and the light-curve features `fe_*` (tsfel) are missing. The classifier never reads catalog columns. It is weak outside GRBs.

Predicted classes over all events: GRB 101, UNC(LP) 17, TGF 7, UNC 5, SF 5, GF 1.

### 6.1 Predicted class against Crupi's tentative classes

Crupi's classes are **tentative** (assigned by hand in the paper, sometimes multiple such as `GRB/GF`): they measure the agreement with his judgement, not the physical nature of the events.

Of 91 events matched to Crupi, predicted class among his tentative ones (multiple included): 79/91 (86.8%).

Confusion matrix on the events with a single Crupi class: **87** events; overall accuracy **75/87 (86.2%)**. Rows: Crupi's class; columns: predicted class.

Counts:

| Crupi class | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 68 | 0 | 0 | 1 | 1 |
| SF | 0 | 4 | 1 | 0 | 0 |
| TGF | 2 | 0 | 0 | 0 | 0 |
| UNC | 0 | 0 | 0 | 0 | 0 |
| UNC(LP) | 5 | 1 | 0 | 1 | 3 |

Row percentages (share of each Crupi class in each predicted class; the diagonal is the recall):

| Crupi class | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 97.1% | 0.0% | 0.0% | 1.4% | 1.4% |
| SF | 0.0% | 80.0% | 20.0% | 0.0% | 0.0% |
| TGF | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC | — | — | — | — | — |
| UNC(LP) | 50.0% | 10.0% | 0.0% | 10.0% | 30.0% |

Column percentages (composition of each predicted class; the diagonal is the precision):

| Crupi class | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 90.7% | 0.0% | 0.0% | 50.0% | 25.0% |
| SF | 0.0% | 80.0% | 100.0% | 0.0% | 0.0% |
| TGF | 2.7% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| UNC(LP) | 6.7% | 20.0% | 0.0% | 50.0% | 75.0% |

Per class (support = events with that Crupi class):

| class | support (Crupi) | predicted | correct | recall % | precision % |
|---|---|---|---|---|---|
| GRB | 70 | 75 | 68 | 97.1% | 90.7% |
| SF | 5 | 5 | 4 | 80.0% | 80.0% |
| TGF | 2 | 1 | 0 | 0.0% | 0.0% |
| UNC | 0 | 2 | 0 | — | 0.0% |
| UNC(LP) | 10 | 4 | 3 | 30.0% | 75.0% |

Per rule, one-vs-rest (as in Crupi's script):

| rule | Crupi positives | rule flags | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|
| GRB | 74 | 79 | 72 | 7 | 2 | 0.91 | 0.97 |
| SF | 6 | 6 | 5 | 1 | 1 | 0.83 | 0.83 |
| TGF | 3 | 4 | 1 | 3 | 2 | 0.25 | 0.33 |
| UNC(LP) | 10 | 15 | 8 | 7 | 2 | 0.53 | 0.80 |
| GF | 2 | 17 | 0 | 17 | 2 | 0.00 | 0.00 |

### 6.2 GBM trigger type against predicted class

GBM catalog triggers matched to one of our events: 67 (each trigger checked to fall in the window of the event it points to, tolerance 8.192 s). The **GBM type is not the physical nature** of the event: it is the classification of the flight software and of the duty scientists (UNCERT and LOCLPAR are uncertain by definition).

Counts (rows: GBM type; columns: predicted class):

| GBM type | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 57 | 0 | 0 | 1 | 1 |
| LOCLPAR | 2 | 0 | 0 | 0 | 1 |
| SFLARE | 0 | 4 | 1 | 0 | 0 |

Row percentages:

| GBM type | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 96.6% | 0.0% | 0.0% | 1.7% | 1.7% |
| LOCLPAR | 66.7% | 0.0% | 0.0% | 0.0% | 33.3% |
| SFLARE | 0.0% | 80.0% | 20.0% | 0.0% | 0.0% |

Agreement with a **HYPOTHETICAL** mapping (GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP), UNCERT→UNC): **62/67 (92.5%)**.

| GBM type | expected class (hypothesis) | matched | agreeing | agreement % |
|---|---|---|---|---|
| GRB | GRB | 59 | 57 | 96.6% |
| LOCLPAR | UNC(LP) | 3 | 1 | 33.3% |
| SFLARE | SF | 5 | 4 | 80.0% |

## 7. Localization

Run: position (PSO on the geometric response of the NaI detectors) for 136/136 events, in `results/events_table_loc.csv`. **Not validated** against reference positions: the coordinates are features of the classifier (distance from Sun and Earth), not a result.

## 8. Engine anomalies

- Predicted background ≤ 0: 212 cells out of 2238398 bins × 36 channels (6 bins with at least one channel, 5 with all). These bins are excluded from S; neighbouring events carry the flag `near_zero_prediction` (6, 9).
- Convergence: final val_loss 4.386, best 4.385 (epoch 57); median test/train MAE over the 36 channels 1.004. Formal convergence check not recorded in the bundle metadata.
- Short SAA passages not masked (data gap ≤ 500 s): 45; the network tends to underestimate the background on the approach (flag `saa_edge_short_passage`).

## 9. Lists by name

Every GBM catalog trigger on the days with data of the period (`validation/list_gbm_grb.csv`, `validation/list_gbm_other.csv`). Outcome: *detected* (matched to one of our events), *missed* (data present, no event), *no data* (SAA mask or data gap).

### 9.1 GRBs (93: detected 59, missed 19, no data 15)

| trigger_name | trigger_time | T90_s | outcome | event_trig_ids | predicted_class |
|---|---|---|---|---|---|
| bn190303240 | 2019-03-03 05:45:22.235 | 64.8 | detected | 1 | GRB |
| bn190304371 | 2019-03-04 08:54:35.515 | 62.2 | no data |  |  |
| bn190304818 | 2019-03-04 19:37:23.342 | 2.9 | detected | 2 | GRB |
| bn190306943 | 2019-03-06 22:37:43.178 | 180.5 | detected | 5 | GRB |
| bn190307151 | 2019-03-07 03:37:16.537 | 75.5 | detected | 7 | GRB |
| bn190308923 | 2019-03-08 22:09:46.740 | 45.6 | missed |  |  |
| bn190310398 | 2019-03-10 09:32:32.569 | 59.4 | detected | 10 | GRB |
| bn190311600 | 2019-03-11 14:23:37.601 | 12.5 | missed |  |  |
| bn190312446 | 2019-03-12 10:42:10.794 | 12.8 | detected | 14 | GRB |
| bn190315512 | 2019-03-15 12:17:42.138 | 29.2 | detected | 16 | GRB |
| bn190319353 | 2019-03-19 08:28:17.514 | 13.9 | no data |  |  |
| bn190319375 | 2019-03-19 09:00:37.980 | 21.8 | no data |  |  |
| bn190320052 | 2019-03-20 01:14:16.488 | 43.0 | detected | 19 | GRB |
| bn190321363 | 2019-03-21 08:42:33.858 | 55.8 | no data |  |  |
| bn190323179 | 2019-03-23 04:17:14.965 | 4.7 | no data |  |  |
| bn190323303 | 2019-03-23 07:16:51.688 | 30.5 | detected | 22 | GRB |
| bn190323548 | 2019-03-23 13:09:04.842 | 1.3 | missed |  |  |
| bn190323879 | 2019-03-23 21:05:19.785 | 38.4 | detected | 23 | GRB |
| bn190324348 | 2019-03-24 08:21:09.629 | 52.2 | detected | 24 | GRB |
| bn190324947 | 2019-03-24 22:44:02.636 | 26.9 | missed |  |  |
| bn190325999 | 2019-03-25 23:58:57.211 | 316.9 | detected | 26 | GRB |
| bn190326314 | 2019-03-26 07:31:38.998 | 55.8 | no data |  |  |
| bn190326975 | 2019-03-26 23:24:41.342 | 20.7 | detected | 27 | GRB |
| bn190327111 | 2019-03-27 02:39:10.973 | 36.9 | detected | 28 | GRB |
| bn190330694 | 2019-03-30 16:39:32.274 | 36.1 | detected | 31 | GRB |
| bn190331093 | 2019-03-31 02:14:37.572 | 4.8 | missed |  |  |
| bn190401139 | 2019-04-01 03:20:20.538 | 42.8 | detected | 32 | GRB |
| bn190404293 | 2019-04-04 07:01:21.925 | 9.5 | missed |  |  |
| bn190406450 | 2019-04-06 10:47:20.324 | 11.8 | detected | 37 | GRB |
| bn190406465 | 2019-04-06 11:09:47.053 | 15.1 | missed |  |  |
| bn190406745 | 2019-04-06 17:52:33.155 | 80.4 | detected | 39 | GRB |
| bn190407575 | 2019-04-07 13:48:36.785 | 58.9 | detected | 41 | GRB |
| bn190407672 | 2019-04-07 16:07:26.493 | 17.7 | detected | 42 | GRB |
| bn190407788 | 2019-04-07 18:54:41.578 | 2.4 | no data |  |  |
| bn190409901 | 2019-04-09 21:38:05.455 | 1.6 | no data |  |  |
| bn190411407 | 2019-04-11 09:45:48.597 | 18.7 | detected | 47 | UNC(LP) |
| bn190411579 | 2019-04-11 13:53:58.091 | 60.9 | detected | 48 | GRB |
| bn190415173 | 2019-04-15 04:09:49.964 | 52.5 | detected | 52 | UNC |
| bn190419414 | 2019-04-19 09:55:37.770 | 212.7 | detected | 54 | GRB |
| bn190420981 | 2019-04-20 23:32:24.966 | 1.5 | detected | 57 | GRB |
| bn190422284 | 2019-04-22 06:48:17.495 | 80.4 | no data |  |  |
| bn190422670 | 2019-04-22 16:05:04.521 | 20.7 | detected | 58 | GRB |
| bn190422957 | 2019-04-22 22:58:24.004 | 213.3 | detected | 60 | GRB |
| bn190425089 | 2019-04-25 02:07:43.545 | 7.7 | missed |  |  |
| bn190427190 | 2019-04-27 04:34:15.081 | 0.4 | no data |  |  |
| bn190428783 | 2019-04-28 18:48:12.460 | 16.6 | detected | 64 | GRB |
| bn190429743 | 2019-04-29 17:49:50.579 | 22.3 | detected | 66 | GRB |
| bn190501794 | 2019-05-01 19:03:42.592 | 425.0 | missed |  |  |
| bn190502168 | 2019-05-02 04:01:30.415 | 11.8 | detected | 68 | GRB |
| bn190504415 | 2019-05-04 09:57:34.203 | 77.6 | detected | 69 | GRB |
| bn190504678 | 2019-05-04 16:16:28.313 | 0.7 | missed |  |  |
| bn190505051 | 2019-05-05 01:14:09.330 | 0.0 | no data |  |  |
| bn190507270 | 2019-05-07 06:28:23.301 | 85.0 | detected | 74 | GRB |
| bn190507712 | 2019-05-07 17:05:16.938 | 0.1 | missed |  |  |
| bn190507970 | 2019-05-07 23:16:29.638 | 36.4 | detected | 76 | GRB |
| bn190508808 | 2019-05-08 19:22:50.400 | 37.6 | detected | 77 | GRB |
| bn190508987 | 2019-05-08 23:41:24.148 | 119.8 | no data |  |  |
| bn190510120 | 2019-05-10 02:52:13.232 | 69.6 | no data |  |  |
| bn190510430 | 2019-05-10 10:19:16.044 | 0.6 | detected | 79 | GRB |
| bn190511302 | 2019-05-11 07:14:24.358 | 27.6 | detected | 80 | GRB |
| bn190512611 | 2019-05-12 14:39:59.722 | 28.2 | detected | 81 | GRB |
| bn190515190 | 2019-05-15 04:33:03.135 | 1.3 | missed |  |  |
| bn190517813 | 2019-05-17 19:30:10.172 | 4.9 | detected | 89 | GRB |
| bn190519309 | 2019-05-19 07:24:57.343 | 43.5 | detected | 90 | GRB |
| bn190525032 | 2019-05-25 00:45:47.652 | 0.9 | missed |  |  |
| bn190530430 | 2019-05-30 10:19:08.903 | 18.4 | detected | 102 | GRB |
| bn190531312 | 2019-05-31 07:29:11.825 | 57.1 | detected | 103 | GRB |
| bn190531568 | 2019-05-31 13:38:03.822 | 0.3 | missed |  |  |
| bn190531840 | 2019-05-31 20:10:12.142 | 38.1 | detected | 104 | GRB |
| bn190601325 | 2019-06-01 07:47:24.176 | 0.6 | missed |  |  |
| bn190603795 | 2019-06-03 19:04:25.984 | 22.5 | detected | 106 | GRB |
| bn190604446 | 2019-06-04 10:42:37.054 | 32.0 | detected | 107 | GRB |
| bn190605974 | 2019-06-05 23:22:27.118 | 3.6 | detected | 108 | GRB |
| bn190606080 | 2019-06-06 01:55:07.776 | 0.2 | detected | 109 | GRB |
| bn190607071 | 2019-06-07 01:42:44.289 | 37.9 | detected | 112 | GRB |
| bn190608009 | 2019-06-08 00:12:18.394 | 85.2 | detected | 113 | GRB |
| bn190609315 | 2019-06-09 07:34:05.259 | 97.5 | detected | 117 | GRB |
| bn190610750 | 2019-06-10 17:59:49.908 | 37.9 | missed |  |  |
| bn190610834 | 2019-06-10 20:00:23.685 | 3.1 | missed |  |  |
| bn190611950 | 2019-06-11 22:47:49.337 | 100.6 | detected | 119 | GRB |
| bn190612165 | 2019-06-12 03:57:24.648 | 144.9 | detected | 120 | GRB |
| bn190613172 | 2019-06-13 04:07:18.234 | 17.1 | detected | 122 | GRB |
| bn190613449 | 2019-06-13 10:47:00.049 | 4.9 | detected | 123 | GRB |
| bn190615636 | 2019-06-15 15:16:27.372 | 16.9 | detected | 125 | GRB |
| bn190619018 | 2019-06-19 00:26:01.777 | 177.9 | detected | 127 | GRB |
| bn190619595 | 2019-06-19 14:16:25.891 | 134.9 | detected | 128 | GRB |
| bn190620507 | 2019-06-20 12:10:10.809 | 51.7 | detected | 129 | GRB |
| bn190622368 | 2019-06-22 08:50:06.276 | 31.7 | missed |  |  |
| bn190623461 | 2019-06-23 11:03:27.095 | 9.7 | no data |  |  |
| bn190626254 | 2019-06-26 06:06:21.684 | 23.8 | detected | 131 | GRB |
| bn190627481 | 2019-06-27 11:31:59.942 | 9.0 | missed |  |  |
| bn190628521 | 2019-06-28 12:30:55.320 | 19.2 | detected | 133 | GRB |
| bn190630257 | 2019-06-30 06:09:58.319 | 0.2 | no data |  |  |

### 9.2 Non-GRB triggers (50: missed 34, no data 8, detected 8)

| type | trigger_name | trigger_time | T90_s | outcome | event_trig_ids | predicted_class |
|---|---|---|---|---|---|---|
| TGF | bn190301418 | 2019-03-01 10:01:15.656 |  | missed |  |  |
| TGF | bn190304208 | 2019-03-04 04:59:50.498 |  | missed |  |  |
| UNCERT | bn190306960 | 2019-03-06 23:02:40.420 |  | missed |  |  |
| TGF | bn190311817 | 2019-03-11 19:36:13.000 |  | missed |  |  |
| LOCLPAR | bn190313150 | 2019-03-13 03:36:00.811 |  | no data |  |  |
| TGF | bn190315717 | 2019-03-15 17:12:28.119 |  | missed |  |  |
| TGF | bn190317700 | 2019-03-17 16:48:02.389 |  | missed |  |  |
| TGF | bn190319608 | 2019-03-19 14:35:16.031 |  | missed |  |  |
| LOCLPAR | bn190320018 | 2019-03-20 00:26:25.614 |  | no data |  |  |
| SFLARE | bn190321613 | 2019-03-21 14:42:03.222 |  | detected | 21 | TGF |
| UNCERT | bn190326747 | 2019-03-26 17:55:54.016 |  | missed |  |  |
| TGF | bn190330372 | 2019-03-30 08:55:36.932 |  | missed |  |  |
| UNCERT | bn190401410 | 2019-04-01 09:51:05.036 |  | missed |  |  |
| TGF | bn190402512 | 2019-04-02 12:16:50.443 |  | missed |  |  |
| LOCLPAR | bn190408536 | 2019-04-08 12:52:18.176 |  | detected | 43 | GRB |
| TGF | bn190417464 | 2019-04-17 11:08:18.409 |  | no data |  |  |
| TGF | bn190418919 | 2019-04-18 22:04:03.328 |  | missed |  |  |
| UNCERT | bn190505818 | 2019-05-05 19:37:53.664 |  | missed |  |  |
| SFLARE | bn190506213 | 2019-05-06 05:06:58.378 |  | detected | 70 | SF |
| SFLARE | bn190506577 | 2019-05-06 13:51:23.127 |  | detected | 71 | SF |
| SFLARE | bn190506742 | 2019-05-06 17:48:10.111 |  | detected | 72 | SF |
| TGF | bn190508107 | 2019-05-08 02:34:25.790 |  | missed |  |  |
| SFLARE | bn190509239 | 2019-05-09 05:43:55.583 |  | detected | 78 | SF |
| TGF | bn190509787 | 2019-05-09 18:53:14.298 |  | missed |  |  |
| LOCLPAR | bn190511253 | 2019-05-11 06:03:42.924 |  | no data |  |  |
| TGF | bn190512623 | 2019-05-12 14:56:32.167 |  | missed |  |  |
| LOCLPAR | bn190513824 | 2019-05-13 19:47:08.098 |  | no data |  |  |
| TGF | bn190514672 | 2019-05-14 16:07:23.939 |  | missed |  |  |
| TGF | bn190514901 | 2019-05-14 21:38:02.170 |  | missed |  |  |
| TGF | bn190515435 | 2019-05-15 10:26:12.748 |  | missed |  |  |
| TGF | bn190515487 | 2019-05-15 11:41:49.478 |  | missed |  |  |
| TGF | bn190515824 | 2019-05-15 19:46:58.291 |  | missed |  |  |
| TGF | bn190517095 | 2019-05-17 02:17:06.248 |  | missed |  |  |
| LOCLPAR | bn190520598 | 2019-05-20 14:21:48.797 |  | detected | 94 | GRB |
| UNCERT | bn190525500 | 2019-05-25 12:00:34.477 |  | missed |  |  |
| TGF | bn190525670 | 2019-05-25 16:04:15.673 |  | missed |  |  |
| TGF | bn190531540 | 2019-05-31 12:58:17.211 |  | missed |  |  |
| TGF | bn190604577 | 2019-06-04 13:51:30.894 |  | missed |  |  |
| LOCLPAR | bn190608859 | 2019-06-08 20:36:53.357 |  | detected | 115 | UNC(LP) |
| TGF | bn190610277 | 2019-06-10 06:38:13.564 |  | no data |  |  |
| TGF | bn190611194 | 2019-06-11 04:39:20.209 |  | missed |  |  |
| TGF | bn190612260 | 2019-06-12 06:13:49.611 |  | no data |  |  |
| TGF | bn190613961 | 2019-06-13 23:03:30.952 |  | missed |  |  |
| UNCERT | bn190619235 | 2019-06-19 05:38:03.136 |  | missed |  |  |
| UNCERT | bn190620579 | 2019-06-20 13:53:27.802 |  | missed |  |  |
| UNCERT | bn190620772 | 2019-06-20 18:31:24.279 |  | missed |  |  |
| UNCERT | bn190620907 | 2019-06-20 21:46:33.246 |  | missed |  |  |
| TGF | bn190622029 | 2019-06-22 00:41:37.810 |  | no data |  |  |
| UNCERT | bn190624976 | 2019-06-24 23:25:16.658 |  | missed |  |  |
| UNCERT | bn190626526 | 2019-06-26 12:36:48.943 |  | missed |  |  |

### 9.3 Crupi's events in the period (95: found 91, not found 4; `validation/list_crupi_events.csv`)

| set | id | catalog_name | trigger_time_utc | CE_Crupi | outcome | event_trig_ids | predicted_class | diagnosis |
|---|---|---|---|---|---|---|---|---|
| known | 2019_1 | GRB190303240 | 2019-03-03 05:45:19 | R | found | 1 | GRB |  |
| known | 2019_2 | GRB190304818 | 2019-03-04 19:37:21 | P | found | 2 | GRB |  |
| known | 2019_4 | GRB190306943 | 2019-03-06 22:37:42 | R | found | 5 | GRB |  |
| known | 2019_5 | GRB190307151 | 2019-03-07 03:37:19 | R | found | 7 | GRB |  |
| known | 2019_6 | GRB190310398 | 2019-03-10 09:32:35 | R | found | 10 | GRB |  |
| known | 2019_7 | GRB190311600 | 2019-03-11 14:23:37 | P | not found |  |  | below threshold: max FOCuS r1 within ±60 s = 2.96 sigma |
| known | 2019_8 | GRB190312446 | 2019-03-12 10:42:13 | R | found | 14 | GRB |  |
| known | 2019_10 | GRB190315512 | 2019-03-15 12:17:44 | R | found | 16 | GRB |  |
| known | 2019_12 | GRB190320052 | 2019-03-20 01:14:21 | R | found | 19 | GRB |  |
| known | 2019_13 | SFLARE19032161 | 2019-03-21 14:42:05 | R | found | 21 | TGF |  |
| known | 2019_14 | GRB190323303 | 2019-03-23 07:16:50 | R | found | 22 | GRB |  |
| known | 2019_15 | GRB190323879 | 2019-03-23 21:05:18 | R | found | 23 | GRB |  |
| known | 2019_16 | GRB190324348 | 2019-03-24 08:21:13 | R | found | 24 | GRB |  |
| known | 2019_17 | GRB190324947 | 2019-03-24 22:44:17 | R | found | 25 | GRB |  |
| known | 2019_18 | GRB190325999 | 2019-03-25 23:58:59 | R | found | 26 | GRB |  |
| known | 2019_19 | GRB190326975 | 2019-03-26 23:24:43 | R | found | 27 | GRB |  |
| known | 2019_20 | GRB190327111 | 2019-03-27 02:39:13 | R | found | 28 | GRB |  |
| known | 2019_22 | GRB190330694 | 2019-03-30 16:39:28 | R | found | 31 | GRB |  |
| known | 2019_23 | GRB190401139 | 2019-04-01 03:20:19 | R | found | 32 | GRB |  |
| known | 2019_27 | GRB190406450 | 2019-04-06 10:47:22 | R | found | 37 | GRB |  |
| known | 2019_28 | GRB190406745 | 2019-04-06 17:52:31 | R | found | 39 | GRB |  |
| known | 2019_29 | GRB190407575 | 2019-04-07 13:48:39 | R | found | 41 | GRB |  |
| known | 2019_30 | GRB190407672 | 2019-04-07 16:07:29 | R | found | 42 | GRB |  |
| known | 2019_31 | LOCLPAR1904085 | 2019-04-08 12:51:22 | R | found | 43 | GRB |  |
| known | 2019_32 | GRB190411407 | 2019-04-11 09:45:46 | R | found | 47 | UNC(LP) |  |
| known | 2019_33 | GRB190411579 | 2019-04-11 13:53:56 | R | found | 48 | GRB |  |
| known | 2019_34 | GRB190415173 | 2019-04-15 04:09:46 | R | found | 52 | UNC |  |
| known | 2019_35 | GRB190419414 | 2019-04-19 09:55:40 | R | found | 54 | GRB |  |
| known | 2019_38 | GRB190420981 | 2019-04-20 23:32:27 | P | found | 57 | GRB |  |
| known | 2019_39 | GRB190422670 | 2019-04-22 16:05:09 | S | found | 58 | GRB |  |
| known | 2019_41 | GRB190422957 | 2019-04-22 22:56:09 | R | found | 60 | GRB |  |
| known | 2019_43 | GRB190428783 | 2019-04-28 18:48:11 | R | found | 64 | GRB |  |
| known | 2019_44 | GRB190429743 | 2019-04-29 17:49:54 | S | found | 66 | GRB |  |
| known | 2019_45 | GRB190502168 | 2019-05-02 04:01:32 | R | found | 68 | GRB |  |
| known | 2019_46 | GRB190504415 | 2019-05-04 09:57:36 | P | found | 69 | GRB |  |
| known | 2019_47 | SFLARE19050621 | 2019-05-06 05:07:05 | R | found | 70 | SF |  |
| known | 2019_48 | SFLARE19050657 | 2019-05-06 13:53:21 | R | found | 71 | SF |  |
| known | 2019_49 | SFLARE19050674 | 2019-05-06 17:47:45 | R | found | 72 | SF |  |
| known | 2019_50 | GRB190507270 | 2019-05-07 06:28:19 | R | found | 74 | GRB |  |
| known | 2019_52 | GRB190507970 | 2019-05-07 23:16:29 | R | found | 76 | GRB |  |
| known | 2019_53 | GRB190508808 | 2019-05-08 19:22:49 | R | found | 77 | GRB |  |
| known | 2019_54 | SFL190509239 | 2019-05-09 05:44:02 | R | found | 78 | SF |  |
| known | 2019_55 | GRB190510430 | 2019-05-10 10:12:57 | R | found | 79 | GRB |  |
| known | 2019_56 | GRB190511302 | 2019-05-11 07:14:26 | R | found | 80 | GRB |  |
| known | 2019_57 | GRB190512611 | 2019-05-12 14:40:04 | R | found | 81 | GRB |  |
| known | 2019_62 | TGF190514901 | 2019-05-14 21:41:40 | P | found | 86 | GRB |  |
| known | 2019_64 | GRB190517813 | 2019-05-17 19:30:08 | R | found | 89 | GRB |  |
| known | 2019_65 | GRB190519309 | 2019-05-19 07:24:53 | R | found | 90 | GRB |  |
| known | 2019_67 | LOCLPAR1905205 | 2019-05-20 14:21:05 | R | found | 94 | GRB |  |
| known | 2019_70 | GRB190530430 | 2019-05-30 10:19:05 | R | found | 102 | GRB |  |
| known | 2019_71 | GRB190531312 | 2019-05-31 07:29:10 | R | found | 103 | GRB |  |
| known | 2019_72 | GRB190531840 | 2019-05-31 20:10:02 | R | found | 104 | GRB |  |
| known | 2019_73 | GRB190603795 | 2019-06-03 19:04:31 | R | found | 106 | GRB |  |
| known | 2019_74 | GRB190604446 | 2019-06-04 10:42:33 | R | found | 107 | GRB |  |
| known | 2019_75 | GRB190605974 | 2019-06-05 23:22:29 | S | found | 108 | GRB |  |
| known | 2019_76 | GRB190606080 | 2019-06-06 01:55:04 | R | found | 109 | GRB |  |
| known | 2019_78 | GRB190607071 | 2019-06-07 01:42:46 | R | found | 112 | GRB |  |
| known | 2019_79 | GRB190608009 | 2019-06-08 00:12:20 | R | found | 113 | GRB |  |
| known | 2019_82 | LOCLPAR1906088 | 2019-06-08 20:35:08 | R | found | 115 | UNC(LP) |  |
| known | 2019_83 | GRB190609315 | 2019-06-09 07:33:36 | R | found | 117 | GRB |  |
| known | 2019_84 | GRB190610750 | 2019-06-10 18:00:05 | R | found | 118 | GRB |  |
| known | 2019_85 | GRB190611950 | 2019-06-11 22:47:46 | R | found | 119 | GRB |  |
| known | 2019_86 | GRB190612165 | 2019-06-12 03:57:24 | R | found | 120 | GRB |  |
| known | 2019_87 | GRB190613172 | 2019-06-13 04:07:21 | R | found | 122 | GRB |  |
| known | 2019_88 | GRB190613449 | 2019-06-13 10:46:58 | R | found | 123 | GRB |  |
| known | 2019_89 | GRB190615636 | 2019-06-15 15:16:26 | R | found | 125 | GRB |  |
| known | 2019_90 | GRB190619018 | 2019-06-19 00:24:24 | R | found | 127 | GRB |  |
| known | 2019_91 | GRB190619595 | 2019-06-19 14:15:55 | R | found | 128 | GRB |  |
| known | 2019_92 | GRB190620507 | 2019-06-20 12:10:10 | R | found | 129 | GRB |  |
| known | 2019_93 | GRB190626254 | 2019-06-26 06:06:24 | P | found | 131 | GRB |  |
| known | 2019_95 | GRB190628521 | 2019-06-28 12:30:54 | R | found | 133 | GRB |  |
| unknown | 2019_0 | UNKNOWN: UNC(LP) | 2019-03-01 09:28:28 | P | not found |  |  | below threshold: max FOCuS r1 within ±60 s = 1.65 sigma |
| unknown | 2019_3 | UNKNOWN: UNC(LP) | 2019-03-06 06:45:30 | R | found | 4 | UNC(LP) |  |
| unknown | 2019_9 | UNKNOWN: GRB | 2019-03-15 05:09:11 | R | found | 15 | GRB |  |
| unknown | 2019_11 | UNKNOWN: GRB | 2019-03-17 01:08:06 | P | found | 18 | GRB |  |
| unknown | 2019_21 | UNKNOWN: GRB | 2019-03-27 06:36:04 | P | found | 29 | GRB |  |
| unknown | 2019_24 | UNKNOWN: SF/GRB | 2019-04-04 12:24:17 | R | found | 33 | GRB |  |
| unknown | 2019_25 | UNKNOWN: GRB | 2019-04-04 13:08:07 | S | found | 34 | GRB |  |
| unknown | 2019_26 | UNKNOWN: UNC(LP) | 2019-04-04 13:45:40 | R | found | 35 | GRB |  |
| unknown | 2019_36 | UNKNOWN: GRB/GF | 2019-04-20 15:08:24 | S | found | 55 | GRB |  |
| unknown | 2019_37 | UNKNOWN: GRB | 2019-04-20 22:32:56 | R | found | 56 | GRB |  |
| unknown | 2019_42 | UNKNOWN: UNC(LP) | 2019-04-28 00:16:26 | R | found | 63 | GRB |  |
| unknown | 2019_51 | UNKNOWN: TGF | 2019-05-07 17:15:13 | P | found | 75 | GRB |  |
| unknown | 2019_58 | UNKNOWN: TGF | 2019-05-14 07:38:41 | P | not found |  |  | below threshold: max FOCuS r1 within ±60 s = 2.87 sigma |
| unknown | 2019_59 | UNKNOWN: UNC(LP) | 2019-05-14 10:31:29 | R | found | 82 | GRB |  |
| unknown | 2019_60 | UNKNOWN: UNC(LP) | 2019-05-14 11:59:58 | R | found | 84 | UNC |  |
| unknown | 2019_61 | UNKNOWN: UNC(LP) | 2019-05-14 13:45:47 | R | found | 85 | SF |  |
| unknown | 2019_63 | UNKNOWN: GRB | 2019-05-15 16:04:20 | P | found | 88 | GRB |  |
| unknown | 2019_66 | UNKNOWN: GRB | 2019-05-20 05:34:01 | R | found | 92 | GRB |  |
| unknown | 2019_68 | UNKNOWN: GRB | 2019-05-24 11:15:53 | S | found | 97 | GRB |  |
| unknown | 2019_69 | UNKNOWN: GRB/TGF | 2019-05-28 23:32:56 | P | found | 99 | GRB |  |
| unknown | 2019_77 | UNKNOWN: GRB/GF | 2019-06-06 13:21:42 | R | found | 110 | GRB |  |
| unknown | 2019_80 | UNKNOWN: UNC(LP) | 2019-06-08 20:22:43 | R | found | 115 | UNC(LP) |  |
| unknown | 2019_81 | UNKNOWN: UNC(LP) | 2019-06-08 20:23:03 | R | not found |  |  | detected but merged: inside our event 115, already matched to 2019_82 2019_80 (Crupi lists them as separate events) |
| unknown | 2019_94 | UNKNOWN: GRB | 2019-06-28 04:23:34 | P | found | 132 | GRB |  |
