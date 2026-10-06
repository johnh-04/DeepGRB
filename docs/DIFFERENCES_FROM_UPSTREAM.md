# Differences from the published code

Reference: Crupi's code, [github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB), branch `master`, commit
`0d7d82c`. Compared folders: `models/`, `utils/`, `pipeline/`, `connections/` (plus `validation/`, which is new).

## How to read

Each row is one difference between the upstream code and the current code, at the level of a file or function.
Behaviour that is the same in both versions is not listed: energy ranges, 4.096 s binning, network architecture and
training recipe, FOCuS update and pruning, trigger condition, merging, offset rule and classification thresholds.
Every row has exactly one category:

- **Equivalent**: same behaviour. This includes pure porting (Keras 3, pandas 2, paths, parallelism, type hints).
- **Intentional deviation**: behaviour or output changes on purpose.
- **Bug fix**: the upstream behaviour was wrong and has been corrected.
- **Inherited limitation**: present in the upstream code and kept on purpose.

The "effect" column says whether the difference changes the results of the official run,
`data/runs/2019-03-01_2019-06-30/engine-v3-seed1`, and gives the evidence. "Undetermined" means the effect cannot be
established from the code and the run files; these items are collected in the last section.

Reference values of the official run:

- Results: 136 events (tiers R/S/P = 102/11/23).
- GBM triggers: 67/120 detected; GRBs 59/78.
- Crupi's tables: 70/71 known and 21/24 unknown events matched.
- Checksums (SHA-256 prefix):
  - `events_table.csv` `eb0207fb7b96acef`
  - `triggers_table.csv` `b430d5e70dc4be9f`
  - `events_table_loc.csv` `0346fec93a02e998`
  - `events_classified.csv` `7924b0d67c200b9e`
  - `events_flags.csv` `338c9e45d999c0f1`

"Earlier network" means the network trained with the same recipe before seeds were fixed. It was used by the runs
`engine-v2` and `engine-v3`, which are kept on disk but are not versioned.

## Summary

| category | items |
|---|---|
| Equivalent | 27 |
| Intentional deviation | 22 |
| Bug fix | 8 |
| Inherited limitation | 8 |
| **total** | **65** |

Ten items have an undetermined effect (see the last section).

## Pipeline entry point (`pipeline/pipeline_bkg.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| analysis period | `start_month="03-2019"`, `end_month="07-2019"`, end month excluded | explicit inclusive dates in USER SETTINGS (`2019-03-01` to `2019-06-30`) | Equivalent | none: same 122 days |
| run orchestration | script runs every step in sequence and overwrites its outputs | status table, one run folder per period, engine version and label, `manifest.json`, resume, outputs never overwritten | Equivalent | none on the tables |
| `add_trig_gbm_to_frg` | adds an `event` column to the observed tables and overwrites them; its `'sqlite:////' + GBM_BURST_DB` concatenates `str` and `Path`, which raises `TypeError` | removed | Equivalent | none: the column is never read |
| diagnostic outputs | network loss plot, SHAP explanation (`explain`), sky map for every event | not produced (sky maps optional) | Intentional deviation | none on the tables |

## Download (`models/download_bkg.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| `download_spec`, completeness | counts the files of a day in `cspec/`; with fewer than 15, deletes the day and downloads it again | checks each expected file; files are staged and validated as FITS before they are moved into place; nothing is deleted or overwritten | Equivalent | none: 122/122 days present (manifest) |
| POSHIST location | `cspec/` | `data/poshist/` | Equivalent | none |
| retries, porting | 4 rounds; `DataFrame.append`; one FTP connection per day | 3 passes; pandas 2; no connection for a day that is already complete | Equivalent | none |

## Preprocess (`models/preprocess.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| POSHIST lookup | in `cspec/` | in `cspec/` and `data/poshist/` | Equivalent | none |
| `build_table` parallelism | `n_jobs=20` | at most 4 workers | Equivalent | none |
| diagnostics | warnings for NaN values and table dimension mismatches | removed | Equivalent | none: messages only |

## Background network (`models/model_nn.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| framework | standalone Keras; losses in `models/utils/losses.py` | Keras 3 through `tensorflow.keras`; losses in `models/losses.py` | Equivalent | none |
| persistence | `.h5` named after the test loss, plus `.txt` and `.png`. With `bool_train=False` it loads the lowest-loss `.h5` and refits the scaler on the current data | bundle: `model.keras`, `scaler.joblib`, `metadata.json` saved and loaded together | Equivalent | none: refitting the scaler on the same data is deterministic |
| unused code paths | keras-tuner search, `model_pretrain`, Huber and MSE losses | removed | Equivalent | none: not called by the upstream pipeline |
| training and seeds | trains at every run, no seeds | trains only when the bundle is missing; seeds of python, numpy and TensorFlow fixed; the official network is retrained with seed 1 | Intentional deviation | measured. Seed 1: 136 events (102/11/23), GBM 67/120, GRB 59/78. Earlier network: 144 events (105/18/21), GBM 68/120, GRB 60/78. Crupi's tables: 70/71 and 21/24 with both networks |
| convergence check | none | non-blocking check recorded in `metadata.json` | Intentional deviation | none: metadata only |
| `predict`, SAA mask at the table edges | `range(max(ind-150, min_index), min(ind+150, max_index))`, with `min_index` and `max_index` the first and last gap: 150 bins before the first gap and after the last gap stay unmasked | clipped to the table | Bug fix | undetermined: at most 2 × 150 bins (first gap at row 9417, last at row 2237805 of 2238398) |
| `predict`, masked rows | `y_pred.loc[set_index] = np.nan` also blanks `met` and `timestamp` | only the rate columns are blanked | Bug fix | none: these rows carry no rates in either version |
| `predict`, zero counts | sets observed zeros to NaN, then tests the same cells for zero to mask the prediction, so the prediction is never masked | observed and predicted cells are masked together | Bug fix | none: 0 zero-count cells outside the rows already masked |
| SAA exclusion | ±150 bins (≈ ±614 s) around data gaps longer than 500 s; the paper text says ±150 s | same | Inherited limitation | none (kept) |
| train/validation/test split | random split (`test_size=0.25`, `random_state=0`; `validation_split=0.3`) of time-correlated bins | same | Inherited limitation | none (kept) |

## FOCuS and triggers (`models/trigs/focus.py`, `models/trigger.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| `focus.py`, guards | no guard | guards for `mu ≤ 0` in `evaluate` and in `xmax` | Equivalent | none: those states are not reached |
| `focus.py`, parameter checks | truthiness tests on `ab_crit` and `mu_min` | `is not None` tests | Equivalent | none: `mu_min = 1.2` |
| `trigger.py`, invalid cells | a zero in any observed or predicted channel of a row turns the whole row into `None` | invalidates only the channel (`x ≤ 0`, `b ≤ 0` or non-finite → `b = NaN`) | Intentional deviation | undetermined: exactly one bin (row 112049) has some, but not all, predicted channels at 0. It lies inside event 6 (rows 112046–112056) and trigger 9 (rows 112049–112056) |
| `trigger.py`, NaN counts | a NaN observed rate with a valid prediction reaches FOCuS without reset | treated as missing, so the curves are reset | Bug fix | none: 0 such cells |
| `trigger.py`, output precision | written with `float_format='%.2f'` | full precision | Intentional deviation | undetermined: rounding can only matter at the 3σ threshold |
| `trigger.py`, parallelism | serial loop over channels | joblib, 4 workers | Equivalent | none |
| FOCuS input | rates (counts/s); the paper describes counts | same | Inherited limitation | none (kept) |
| `t_max` | 50 bins (204.8 s); the paper gives `dmax` = 120.4 s | same | Inherited limitation | measured on the earlier network: run `engine-v2-sens-tmax29` (29 bins = 118.8 s) gives the same counts as `engine-v2` (144 events, GBM 68/120, Crupi 70/71 and 21/24), but a different `events_table.csv` (`779f02352e859a83` vs `78f547180badac51`) |
| `MAX_DET_NUMBER` | 13, exclusive upper bound; with 12 NaI it never vetoes | same | Inherited limitation | none (kept) |

## Events (`models/analyze.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| `fetch_triggers`, `merge`, offset rule, `trig_dets` | trigger in r1, inclusive slice, merge within 600 s, start extended by the FOCuS offset (`min` offset + 1), detectors above threshold in any range | same, ported to pandas 2 | Equivalent | none |
| `catalog_triggers` | set order | sorted | Equivalent | none |
| `SC_poisson`, rounding | `(n-b).sum() / np.sqrt(b.sum()).round(2)`: operator precedence rounds √ΣB to 2 decimals | exact √ΣB | Bug fix | the event list does not depend on S, and the sign of S is unchanged, so the tiers are unchanged. The size of the change in the S values is undetermined |
| `SC_poisson`, missing values | any NaN in the window makes `np.quantile` NaN, so S = 0 for that range | invalid bins are dropped | Bug fix | undetermined |
| `SC_poisson`, predicted B ≤ 0 (engine v3) | bins kept | bins with predicted background ≤ 0 excluded from S | Intentional deviation | measured with seed 1, v2 vs v3: only event 6 changes. S_r0 880.92 → 29.11, S_r1 764.87 → 25.70, S_r2 99.17 → 14.25, quantile 0.7/0.7/0.6 → 0.85. With the earlier network `engine-v2` and `engine-v3` have identical tables (`78f547180badac51`, triggers `e9bab9e9…`) |
| end index | no guard when an event ends on the last bin | guarded | Bug fix | none: no event ends on the last bin |
| new columns | none | `detectors`, `sigma_C`, `CE` (tier R/S/P) | Intentional deviation | columns only |
| other outputs | `stat_table.csv`, `summary.txt`, plots, exports, `reduce_table`, other significance types | not produced | Intentional deviation | none on the tables |
| S on rates | S computed from rates | same | Inherited limitation | none (kept) |

## Localization (`models/localize_event.py`, `models/loc/localization_class.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| residual source | rates from the daily table (unmasked) merged with the prediction | observed table of the run (masked) minus the prediction | Equivalent | none: the prediction is NaN in masked rows in both versions, and there are 0 zero-count cells |
| pointing, POSHIST | exact `met` merge; POSHIST downloaded over FTP | nearest `met` in the daily table; local POSHIST | Equivalent | none |
| PSO seed | global numpy state, no seed | per-event seed (42 + `trig_ids`) | Intentional deviation | measured: the rerun `engine-v3-verify1` gives an identical `events_table_loc.csv`. The Monte Carlo uses `np.random.seed(42)` and 250 samples in both versions |
| rounding of positions | `ra`, `dec`, Monte Carlo means rounded to 0 decimals | 2 decimals | Intentional deviation | undetermined effect on the classes |
| `ra_std`, `dec_std` | stores the variance `cov[0][0]` | stores the standard deviation | Bug fix | none on the classes: the classifier threshold moves from 100 deg² to 10 deg |
| bound guards | PSO amplitude bound `max_c`; Monte Carlo L-BFGS-B upper bound `max*2` | `max(max_c, min_c+1)`; `max*2+1` | Intentional deviation | undetermined |
| peak search | maximum residual over all channels | channels with predicted background ≤ 0 excluded | Intentional deviation | undetermined: in the peak row of event 6, 10 of the 12 channels have invalid background; 136/136 events are localized |
| new column | none | `loc_range` | Intentional deviation | column only |

## Classification (`models/event_classifier.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| rules | offline scripts (`script_classification2.py`, `classification_logic`). SF, TGF, GF, UNC(LP), FP and GRB rules with fixed thresholds | pipeline step, same thresholds | Equivalent | none |
| single label | one-vs-rest outputs or a random forest | `predicted_class` with priority GRB, TGF, SF, UNC(LP), GF, UNC; one-vs-rest columns kept | Intentional deviation | new column |
| hardness ratios | `min(σ_r1/σ_r0, 10)`: division by zero gives inf → 10, or 0/0 → NaN | `σ_r0 ≤ 0` replaced by 1e-4 before the division, then capped at 10 | Intentional deviation | measured: none. 44 events have σ_r0 = 0 and HR10 = 10 in both versions; 0 events have σ_r0 = σ_r1 = 0; HR10 and HR21 are identical for all 136 events |
| `earth_vis` | NaN reaches the rules | NaN filled with 1 | Intentional deviation | none: 0 NaN |
| `num_det_rng` | `len + 1` | `len` | Equivalent | none: not used by the rules |
| catalog columns | read by the labelling scripts | not read by the classifier | Equivalent | none |
| FP rule, `fe_*` features | FP rule on `fe_bkg` features; `fe_wet` and `fe_skw` terms in GRB and UNC(LP) | no FP rule; `fe_wet` = 2.1 and `fe_skw` = 0.0, so those terms are neutral | Inherited limitation | undetermined: the features are not available |
| thresholds | learned on 2010-11, 2014 and 2019 | same | Inherited limitation | none (kept); 2019 is not independent of the thresholds |

## Validation (`validation/`, `models/flags.py`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| matching rule | `check_against_gbmcatalogs`: a GRB is detected when the FOCuS trigger condition holds inside the catalog interval `[time, end_time]` | one-to-one matching of the catalog trigger instant within the event ±2 bins | Intentional deviation | measured: GBM 67/120, GRB 59/78 (T90 > 4.096 s 54/65, ≤ 4.096 s 5/13) |
| scope | GRBs only | all trigger types, Crupi's tables, sensitivity windows, classification metrics, `RESULTS.md` | Intentional deviation | new outputs: Crupi 70/71 and 21/24; accuracy 75/87 (86.2%); GBM type agreement 62/67 |
| data availability | missing when any NaN is in the FOCuS table within ±1 bin of the trigger | available when any channel has a finite prediction within 1 bin | Intentional deviation | undetermined: 15 GRBs without data, as in the paper |
| flags | none | `models/flags.py` | Intentional deviation | columns only: 31 of the 46 events without a counterpart are flagged |

## Utilities and catalogs (`utils/`, `connections/`)

| file / function | upstream | this repository | category | effect |
|---|---|---|---|---|
| `utils/keys.py` | includes `filter_keys` | removed | Equivalent | none |
| configuration | `models/utils/config.py` with user-specific paths; empty `utils/config.py` | single `connections/utils/config.py` | Equivalent | none |
| MET conversion | `gbm` `Met` | `utils/fermi_time.py` | Equivalent | none: verified equal to `gbm` `Met` |
| trigger catalog | interval `time` → `end_time` | same interval, plus `trig_met`, `trigger_name`, `trigger_timescale` | Intentional deviation | none: the new columns are used only by the validation |
| detector mask, raw catalog | mask string format; `df_burst_catalog_raw` | normalised format; function removed | Equivalent | none |
| burst catalog | flux columns computed but not stored | flux columns stored | Intentional deviation | none: only T90 is used |
| new modules | none | `utils/period.py`, `utils/run_options.py`, `utils/logs.py` | Equivalent | none |

## Files

Upstream files that are no longer in the tree (their behaviour, where it matters, is covered by the rows above):

- `models/load_data.py`, `models/trigs/paramtrig.py`, `models/utils/GBMutils.py`, `models/utils/__init__.py`
- `models/utils/config.py`, `utils/config.py`: replaced by `connections/utils/config.py`
- `models/utils/losses.py`: moved to `models/losses.py`
- `models/tests/test_merge_events.py`, `models/tests/test_trigger_condition.py`
- `pipeline/pipeline_bkg_2.py`, `pipeline/read_catalog_to_mv.py`, `pipeline/script_to_latex.py`
- `pipeline/script_classification.py`, `pipeline/script_classification2.py`, `pipeline/manual_label.py`,
  `pipeline/run_classification.txt`: the rules are in `models/event_classifier.py`
- outside the compared folders: `scripts/` (variational autoencoder, redshift and background studies), `readme.txt`,
  `data/DeepGRB_catalog.csv`

New files: `models/event_classifier.py`, `models/flags.py`, `models/losses.py` (moved), `models/loc/pyswarms_logging.yaml`,
`utils/fermi_time.py`, `utils/period.py`, `utils/run_options.py`, `utils/logs.py` and `validation/` (`validate.py`,
`report.py`, `report_tables.py`, `matching.py`, `reference/crupi_2019_known.csv`, `reference/crupi_2019_unknown.csv`).

## Undetermined

These effects cannot be established from the code and the run files without running the upstream code on the same
data:

1. SAA mask at the table edges (network): whether the 150 bins before the first gap and after the last gap, which
   upstream left unmasked, would have produced triggers.
2. Per-channel invalidation in `trigger.py`: its effect on event 6 (bin 112049, trigger 9).
3. `%.2f` rounding of the upstream FOCuS output: triggers at the 3σ threshold.
4. Rounding of √ΣB in `SC_poisson`: the size of the change in the S values and in the selected quantile.
5. S = 0 for windows that contain a NaN (upstream): which events and ranges are affected.
6. Rounding of the positions to 0 decimals (upstream): effect on the classes.
7. PSO and Monte Carlo bound guards in the localization.
8. Exclusion of channels with predicted background ≤ 0 from the localization peak: whether the peak of event 6 moves.
9. Data-availability rule in the validation: which GRBs change status (the total of 15 matches the paper).
10. Missing FP rule and `fe_*` features in the classification: the classes upstream would assign.
