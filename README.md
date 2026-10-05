# DeepGRB

<img src="https://user-images.githubusercontent.com/93478548/189541951-83a118d4-0a6f-41f3-bc57-cbf0ab7623c2.png" width="750">

**DeepGRB** searches Fermi/GBM data for astronomical transients: a neural network estimates the background count rates
of the 12 NaI detectors from the orbital state of the spacecraft, and the Poisson-FOCuS trigger algorithm looks for
significant excesses over that background.

This repository is a reproducible version of DeepGRB that reproduces the 2019 results of Crupi et al. (2023), maintained
by **Giovanni Pio Martello** (Politecnico di Bari, bachelor's thesis with Prof. Elisabetta Bissaldi; ReCaS Bari cluster).

## Credits

DeepGRB was created by **Riccardo Crupi** and **Giuseppe Dilillo**, with Elisabetta Bissaldi, Kester Ward,
Fabrizio Fiore and Andrea Vacchi. Original repository: [github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB).

- **Searching for long faint astronomical high energy transients: a data driven approach.** Riccardo Crupi, Giuseppe
  Dilillo, Kester Ward, Elisabetta Bissaldi, Fabrizio Fiore, Andrea Vacchi. Experimental Astronomy 56, 421 (2023).
  https://link.springer.com/article/10.1007/s10686-023-09915-7
- Poisson-FOCuS: An efficient online method for detecting count bursts with application to gamma ray burst detection.
  Kester Ward, Giuseppe Dilillo, Idris Eckley, Paul Fearnhead. https://arxiv.org/abs/2208.01494

License: MIT (see `LICENSE`).

## The pipeline

`pipeline/pipeline_bkg.py` runs nine steps. A step whose outputs exist is skipped, so a run with everything in place
ends right after the status table.

| step | what | output |
|---|---|---|
| 1 | download CSPEC (12 NaI + 2 BGO) and POSHIST files of every day of the period (idempotent) | `data/cspec/`, `data/poshist/` |
| 2 | preprocess: 36 count rates (12 NaI × 28–50, 50–300, 300–500 keV) and orbital features, 4.096 s bins | `data/bkg/YYMMDD.csv` |
| 3 | background estimated by a neural network (one network per period, trained only on request) | `<run>/pred/{frg,bkg}.csv` |
| 4 | Poisson-FOCuS on the rates (mu_min 1.2, t_max 50 bins) | `<run>/trig/` |
| 5 | triggers (3σ in 50–300 keV on ≥ 1 detector), events (merge within 600 s), significance S, tier R/S/P | `<run>/results/events_table.csv` |
| 6 | localization (PSO) and Crupi's heuristic classification | `<run>/results/events_classified.csv` |
| 7 | post-processing flags (SAA edge, SAA region, near-zero background) | `<run>/results/events_flags.csv` |
| 8 | validation against the Fermi-GBM trigger catalog (always) and Crupi's tables (2019 only) | `<run>/validation/` |
| 9 | report of the run | `<run>/RESULTS.md` |

The scientific parameters are those of the code that produced the paper; they live in `connections/utils/config.py`.
Differences from the published code are listed in `docs/DIFFERENCES_FROM_UPSTREAM.md`.

## Folders

```
pipeline/pipeline_bkg.py      entry point: USER SETTINGS, status table, the 9 steps
connections/utils/config.py   the single configuration: folders, engine version, scientific parameters
connections/fermi_data_tools.py  Fermi-GBM trigger and burst catalogs from HEASARC
utils/                        channel keys, periods, UTC <-> MET, run options and manifest, logging
models/                       the engine (steps 1-7): download_bkg, preprocess, model_nn (+ losses),
                              trigger + trigs/focus (Poisson-FOCuS), analyze, localize_event + loc/,
                              event_classifier, flags
validation/                   steps 8-9: validate, report, report_tables, matching,
                              reference/ (Tables 10 and 11 of Crupi et al.)
docs/                         project overview, 2019 baseline, validation method, differences from upstream
data/                         inputs, models and runs (see data/README.md; mostly not versioned)
```

A run lives in `data/runs/<start>_<end>/engine-v<N>[-<label>]/`: `<start>_<end>` is the period, `v<N>` the engine
version and `<label>` names the network. The official run is **`data/runs/2019-03-01_2019-06-30/engine-v3-seed1`**: engine v3, network
trained with seed 1. It holds `manifest.json` (parameters, model, executions), `pred/` and `trig/`
(steps 3-4, not versioned), `results/` (steps 5-7), `validation/` (step 8) and `RESULTS.md` (step 9).

## Requirements

Python 3.9 and the pinned packages of `requirements.txt` (`gbm-data-tools` is installed from the NASA tarball listed
there). A GPU is needed only to train a network; everything else runs on CPU (4 cores and 16 GB are enough).

## Running

Settings are in the **USER SETTINGS** block at the top of `pipeline/pipeline_bkg.py`:

```python
START_DATE = "2019-03-01"   # first UTC day, included
END_DATE = "2019-06-30"     # last UTC day, included
RUN_LABEL = "seed1"         # official 2019 run engine-v3-seed1; None = unlabelled run
TRAIN_SEED = None           # integer seed; required with FORCE_TRAIN
FORCE_TRAIN = False         # train a new network (needs RUN_LABEL and TRAIN_SEED)
...
```

Every setting can also be given as an environment variable `DEEPGRB_<NAME>`, which has priority (list in
`utils/run_options.py`). From the repository root:

```bash
python -u pipeline/pipeline_bkg.py --dry-run          # status table and steps to run, writes nothing
nohup python -u pipeline/pipeline_bkg.py --jobs 4 > logs/pipeline.out 2>&1 &

# another period with a new network (hours on GPU)
DEEPGRB_START_DATE=2024-05-01 DEEPGRB_END_DATE=2024-05-31 DEEPGRB_RUN_LABEL=seed1 \
DEEPGRB_TRAIN_SEED=1 DEEPGRB_FORCE_TRAIN=1 nohup python -u pipeline/pipeline_bkg.py > logs/may2024.out 2>&1 &
```

The log goes to stdout and to `logs/`. An existing run only resumes its missing steps and the outputs of steps 3-7 are
never overwritten; a run whose recorded parameters or model checksum differ from the current ones stops; training needs
an explicit seed and a label. How to rerun the baseline from its network is in `docs/BASELINE_2019.md`.

## Reading RESULTS.md

Every run has the same sections: (1) period, network (bundle, seed, checksum) and parameters; (2) events and tiers
R/S/P; (3) Fermi-GBM catalog: triggers by type, GRBs by T90, sensitivity to the matching window; (4) comparison with
Crupi et al. and acceptance criteria (2019 only); (5) events without counterpart, by flag; (6) classification: confusion
matrix against Crupi's tentative classes (counts, row and column percentages, recall, precision, support, accuracy) and
GBM trigger type against predicted class; (7) localization; (8) engine anomalies; (9) lists by name of every GBM
trigger and Crupi event, with outcome and predicted class. The method is described in `docs/VALIDATION.md`.

## The 2019 baseline

Official run `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`, period 2019-03-01 → 2019-06-30 (122 days with data):

| quantity | value |
|---|---|
| events (CE tiers R / S / P) | 136 (102 / 11 / 23) |
| GBM catalog triggers detected / available | 67/120 (55.8%) |
| GRBs detected / available | 59/78 (75.6%) |
| GRBs with T90 > 4.096 s / ≤ 4.096 s | 54/65 (83.1%) / 5/13 (38.5%) |
| Crupi's known events found (Table 11, in the period) | 70/71 (98.6%) |
| Crupi's unknown events found (Table 10, in the period) | 21/24 (87.5%) |
| unknown R+S events found | 15/16 (93.8%) |
| events without counterpart (with at least one flag) | 46 (31) |
| classification vs Crupi's tentative classes (single-label events) | accuracy 75/87 (86.2%) |
| GBM trigger type vs predicted class (hypothetical mapping) | 62/67 (92.5%) |

Classification against Crupi's tentative classes, events with a single class:

| class | support (Crupi) | predicted | correct | recall % | precision % |
|---|---|---|---|---|---|
| GRB | 70 | 75 | 68 | 97.1% | 90.7% |
| SF | 5 | 5 | 4 | 80.0% | 80.0% |
| TGF | 2 | 1 | 0 | 0.0% | 0.0% |
| UNC | 0 | 2 | 0 | — | 0.0% |
| UNC(LP) | 10 | 4 | 3 | 30.0% | 75.0% |

Details, checksums and how to reproduce: `docs/BASELINE_2019.md`; full report: `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/RESULTS.md`.

## Scope

- Events without counterpart are candidates, not discoveries: 31 of the 46 carry a
  post-processing flag (SAA edge or region, near-zero background).
- Localization is not validated: positions are used as classifier features only.
- The classifier is Crupi's heuristic baseline: good on GRBs, weak on the other classes.
- Crupi's tables cover 2019-03-01 → 2019-07-09; the baseline stops at 2019-06-30.

## Open work

- A learned classifier (XGBoost) trained on Crupi's labelled events of 2010-11, 2014 and 2019, to outperform the
  heuristic baseline.
- Runs on 2024 data (solar cycle 25 maximum), one network per period.
