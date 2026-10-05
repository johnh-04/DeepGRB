# Differences from the published code

Comparison with Crupi's code ([github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB), branch `master`). The
modules keep their names and places, so each one can be compared file by file.

## Same science

- **Poisson-FOCuS** (`models/trigs/focus.py`): same update, pruning, `mu_min` and `t_max`; NaN reset the curves. Only
  defensive guards (`mu ≤ 0`, `|b| ≈ 0`) were added; they do not change any reachable result.
- **FOCuS driver** (`models/trigger.py`): runs the 36 channels in parallel (joblib) and writes full-precision CSV;
  inputs are read-only and missing or non-positive cells reach FOCuS as NaN.
- **Preprocess** (`models/preprocess.py`): same energy ranges, 4.096 s rebinning, rates and POSHIST features; also looks
  for POSHIST files in `data/poshist/`.
- **Background network** (`models/model_nn.py`): same architecture and training recipe (Nadam, β₂ = 0.99, step learning
  rate ×12.5 for 4 epochs, ×2 until epoch 12, ÷2 afterwards, validation split 0.3, early stopping with patience 32 and
  `min_delta` 0.01, split seed 0, batch 2048); training excludes the SAA and the intervals of the GBM triggers.
- **Events** (`models/analyze.py`): upstream event construction — trigger condition on range r1, merge within 600 s,
  inclusive end index, start extended by the FOCuS offset, per-event S maximised over 21 quantile cuts.
- **Trigger catalog** (`connections/fermi_data_tools.py`): same interval semantics (`time` → `end_time`) used to
  exclude GBM triggers from training; the trigger instant is added for matching.
- **Classification rules** (`models/event_classifier.py`): Crupi's manual classification logic
  (`pipeline/script_classification2.py` upstream).

## Paper text and code

In three places the published code, which produced the results of the paper, differs from the text of the paper. This
repository follows the code:

| topic | paper text | code (followed here) |
|---|---|---|
| FOCuS input | counts per bin | rates (counts/s) |
| SAA exclusion | ±150 s around SAA passages ≥ 500 s | ±150 bins (≈ ±614 s) around data gaps > 500 s |
| FOCuS `t_max` | `dmax` = 120.4 s | 50 bins (204.8 s) |

## Corrections

- Timestamps are UTC, through one MET ↔ UTC conversion (`utils/fermi_time.py`).
- The network, its `StandardScaler` and a `metadata.json` (period, seed, hyper-parameters, per-channel MAE, versions)
  are saved together as a bundle and always loaded together; the seeds of python, numpy and TensorFlow are fixed and
  recorded. Upstream refitted the scaler on the current data.
- Predicted rates: the SAA mask and zero-count cells are NaN in both observed and predicted tables, only on the rate
  columns; inputs are never overwritten.
- Event significance: bins with missing values or with predicted background ≤ 0 are ignored in S (engine v3); the
  consistency C = max(S_r0, S_r1, S_r2) and the tier R/S/P are added.
- Localization: `ra_std` and `dec_std` are standard deviations (upstream stored the variance); one seed per event
  makes parallel runs reproducible.
- Classification: the predicted class depends only on physical features; catalog columns are kept apart for evaluation.
  The FP rule and the light-curve features `fe_*` (computed with tsfel in the upstream branch `ric_review_28062023`) are
  not available, so the terms that use them are neutral. Each rule is reported one-vs-rest; the single label follows the
  priority GRB, TGF, SF, UNC(LP), GF, UNC.
- Download: explicit inclusive dates, one day column, per-file retry and validation, idempotent (an existing day opens
  no connection).

## Added

- Explicit, inclusive analysis period set in one place (USER SETTINGS of the pipeline).
- One run folder per period, engine version and network label, with a manifest and safety rules.
- Post-processing flags (`models/flags.py`).
- Validation with one-to-one matching against the GBM catalogs and Crupi's tables, and a report per run (`validation/`).

## Not carried over

Plots of light curves and localizations, SHAP explanations, hyper-parameter search (keras-tuner), the per-period
`stat_table.csv` and `summary.txt`, and the scripts for the variational autoencoder and redshift studies.
