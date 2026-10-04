# DeepGRB

<img src="https://user-images.githubusercontent.com/93478548/189541951-83a118d4-0a6f-41f3-bc57-cbf0ab7623c2.png" width="750">

**DeepGRB** searches Fermi/GBM data for astronomical transients: a neural network estimates the
background count rates of the 12 NaI detectors from the orbital state of the spacecraft, and the
Poisson-FOCuS trigger algorithm looks for significant excesses over that background.

This repository is a **consolidated version** of DeepGRB, maintained by **Giovanni Pio Martello**
(Politecnico di Bari, master's thesis with Prof. Elisabetta Bissaldi; runs on the ReCaS Bari
cluster and its Jupyter service). It reproduces the 2019 results of Crupi et al. (2023) with
verifiable code and is the base for a learned classifier (XGBoost) and for the 2024 data.

## Credits

DeepGRB was created by **Riccardo Crupi** and **Giuseppe Dilillo**, with Elisabetta Bissaldi,
Kester Ward, Fabrizio Fiore and Andrea Vacchi. Original repository:
[github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB). Please cite:

- **Searching for long faint astronomical high energy transients: a data driven approach.**
  Riccardo Crupi, Giuseppe Dilillo, Kester Ward, Elisabetta Bissaldi, Fabrizio Fiore, Andrea Vacchi.
  Experimental Astronomy 56, 421 (2023). https://link.springer.com/article/10.1007/s10686-023-09915-7
- Poisson-FOCuS: An efficient online method for detecting count bursts with application to gamma ray
  burst detection. Kester Ward, Giuseppe Dilillo, Idris Eckley, Paul Fearnhead.
  https://arxiv.org/abs/2208.01494

Consolidation, validation against the paper and maintenance of this version: Giovanni Pio Martello.
License: MIT (see `LICENSE`).

## The pipeline

`pipeline/pipeline_bkg.py` is the only entry point. It runs nine steps; each step is skipped when its
outputs already exist, so a run with everything in place ends right after the status table.

| step | what | output |
|---|---|---|
| 1 | download CSPEC (12 NaI + 2 BGO) and POSHIST files of every day of the period (idempotent) | `data/cspec/`, `data/poshist/` |
| 2 | preprocess: 36 count rates (12 NaI × 28–50, 50–300, 300–500 keV) and orbital features, 4.096 s bins | `data/bkg/YYMMDD.csv` |
| 3 | neural background (one network per period; training only on request) | `<run>/pred/{frg,bkg}.csv` |
| 4 | Poisson-FOCuS on the rates (mu_min 1.2, t_max 50 bins) | `<run>/trig/` |
| 5 | triggers (3σ in 50–300 keV on ≥ 1 detector), events (merge within 600 s), significance S and tier R/S/P | `<run>/results/events_table.csv` |
| 6 | localization (PSO, slow) and Crupi's heuristic classification | `<run>/results/events_classified.csv` |
| 7 | post-processing flags (SAA edge, SAA region, near-zero background) | `<run>/results/events_flags.csv` |
| 8 | validation: official GBM catalog (always), Crupi's tables (2019 only) | `<run>/validation/` |
| 9 | report of the run and index of all runs | `<run>/RESULTS.md`, `docs/RUNS.md` |

Parameters are those of the upstream code that produced the paper (three places where the code differs
from the paper text are documented in `docs/WORKING_RULES.md` §2); they live in `connections/utils/config.py`.

## Requirements

Python 3.9 and the pinned packages of `requirements.txt` (the environment used for the 2019 baseline):

```
pip install -r requirements.txt
```

`gbm-data-tools` is installed from the NASA tarball listed there. A GPU is needed only to train a
network (step 3 with `FORCE_TRAIN`); everything else runs on CPU (4 cores, 16 GB on ReCaS).

## Running

Edit the **USER SETTINGS** block at the top of `pipeline/pipeline_bkg.py`:

```python
START_DATE = "2019-03-01"   # first UTC day, included
END_DATE = "2019-06-30"     # last UTC day, included
RUN_LABEL = None            # e.g. "seed1": separate run folder and model bundle
TRAIN_SEED = None           # integer seed; required with FORCE_TRAIN
FORCE_TRAIN = False         # train a new network (needs RUN_LABEL and TRAIN_SEED)
...
```

Every setting can also be given as an environment variable `DEEPGRB_<NAME>`, which has priority
(full list in `utils/run_options.py`). Then, from the repository root:

```bash
python -u pipeline/pipeline_bkg.py --dry-run          # status table and steps to run, writes nothing
nohup python -u pipeline/pipeline_bkg.py --jobs 4 > logs/pipeline.out 2>&1 &

# the 2019 reference run (retrained network, seed 1), reusing existing data
DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 nohup python -u pipeline/pipeline_bkg.py > logs/seed1.out 2>&1 &

# a new network for a new period (hours on GPU)
DEEPGRB_START_DATE=2024-05-01 DEEPGRB_END_DATE=2024-05-31 DEEPGRB_RUN_LABEL=seed1 \
DEEPGRB_TRAIN_SEED=1 DEEPGRB_FORCE_TRAIN=1 nohup python -u pipeline/pipeline_bkg.py > logs/may2024.out 2>&1 &
```

The log is printed on stdout and written to `logs/`. Safety rules: a new labelled run never reuses a
folder; an existing run only resumes its missing steps and outputs of steps 3–7 are never overwritten;
a run whose recorded parameters or model checksum differ from the current ones stops; training needs an
explicit seed and a label.

## Folders

```
pipeline/pipeline_bkg.py      entry point (USER SETTINGS, status table, 9 steps)
connections/                  configuration (utils/config.py) and Fermi/GBM catalogs from HEASARC
utils/                        channel keys, periods, Fermi time, run options and manifest, logging
models/                       download, preprocess, background network, FOCuS (trigs/), events,
                              localization (loc/), classifier, flags, losses
benchmark/                    validation (validate.py), reports (report.py), matching, reference tables,
                              audit/ and analysis/ tools used to regenerate the documents in docs/
tests/                        unit tests (python -m unittest discover -s tests -t .)
docs/                         baseline, runs, analyses, worklog, refactoring report
data/                         inputs, models and runs (mostly not versioned, see data/README.md)
```

A run lives in `data/runs/<start>_<end>/engine-v<N>[-<label>]/` with `manifest.json` (parameters,
model, history), `pred/`, `trig/`, `results/`, `validation/` and `RESULTS.md`. The engine version
changes when a code change alters the events, so old results are never mixed with new code.

## Reading RESULTS.md

Every run has the same sections: (1) period, network (bundle, seed, checksum) and parameters;
(2) events and tiers R/S/P; (3) official GBM catalog: triggers by type, GRB by T90, sensitivity to the
matching window (2 bins, 10, 60, 1200 s); (4) comparison with Crupi et al. with ✔/✘ acceptance
criteria (2019 only); (5) events without counterpart, split by flag; (6) classification against the
reference; (7) localization; (8) engine anomalies (predicted background ≤ 0, convergence, stability).
`docs/RUNS.md` has one line per run.

## Example: the 2019 baseline

<!-- BASELINE:START (generated by python -m benchmark.baseline_doc; do not edit) -->
Reference run `data/runs/2019-03-01_2019-06-30/engine-v3-seed1` (network `model_2019-03-01_2019-06-30_seed1`), from its `RESULTS.md`:

- events: **136** (R 102, S 11, P 23);
- Crupi et al., known events (Table 11, up to 2019-06-30): **70/71 (98.6%)**; unknown events (Table 10): **21/24 (87.5%)**, R+S 15/16 (93.8%);
- official GBM triggers detected: 67/120 (55.8%); GRB 59/78 (75.6%) (T90 > 4.096 s 54/65 (83.1%), ≤ 4.096 s 5/13 (38.5%));
- events without counterpart: 46 (candidates, not discoveries; 31 of them with at least one post-processing flag).

With the legacy network (`data/runs/2019-03-01_2019-06-30/engine-v3`): 144 events, known 70/71, unknown 21/24, 53 without counterpart. Details: `docs/BASELINE_2019.md`, `docs/RUNS.md`.
<!-- BASELINE:END -->

## Scope and limits

- **Events without counterpart are candidates, not discoveries.** Most of them are flagged near the SAA.
- **Localization is not validated**: positions are used as classifier features only.
- **The classifier is Crupi's heuristic baseline**: good on GRB, weak on the other classes; the FP rule
  and the light-curve features `fe_*` (tsfel) are missing.
- The number of events depends on the network (legacy vs retrained): see the stability line of RESULTS.md.
- The paper covers 2019-03-01 → 2019-07-09; this baseline stops at 2019-06-30 (4 reference events out of scope).

## What changed with respect to the original code

Fixed (details in `docs/WORKLOG.md` and `docs/DIFF_UPSTREAM.md`): per-event significance attached to the
wrong events, catalog labels leaking into the classifier, SAA mask destroyed and inputs overwritten before
FOCuS, a broken download, a model that could not be reloaded and an unsaved scaler, a time window that
included days without data; predicted background ≤ 0 is now invalid in S (engine v3). Added: one-to-one
validation against the GBM catalog and Crupi's tables, post-processing flags, labelled runs with explicit
training seeds, a single entry point and a report per run. The consolidation (one configuration, one
logging, no legacy code) is described in `docs/REFACTOR_REPORT.md`.

## Open work

- XGBoost classifier on Crupi's labelled events of 2010-11, 2014 and 2019 (`docs/WORKING_RULES.md`, phase 6;
  Crupi's scripts kept in `docs/legacy_crupi/`).
- Runs on 2024 data (solar cycle 25 maximum): one network per period.
