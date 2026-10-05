# DeepGRB — project overview

## What it is

DeepGRB looks for gamma-ray transients in Fermi/GBM data. A feed-forward neural network predicts, every
4.096 s, the background count rates of the 12 NaI detectors in three energy ranges from the orbital state of
the spacecraft (position, attitude, velocity, Sun and Earth geometry, McIlwain L, detector pointings). Poisson-FOCuS
then searches the observed rates for significant excesses over that background. Excesses become events, which are
characterised (significance, detectors, energy ranges, tier), localized, classified, flagged, and compared with the
official Fermi-GBM trigger catalog and with the tables of Crupi et al. (2023).

This repository is a reproducible baseline of the method published by Crupi et al. on 2019-03-01 → 2019-06-30. It keeps
the structure of the original code (`connections/`, `utils/`, `models/`, `pipeline/`) so that every module can be
compared with the published one (`docs/DIFFERENCES_FROM_UPSTREAM.md`).

## The pipeline

`pipeline/pipeline_bkg.py` is the only entry point. Settings (period, run label, training) are in its USER SETTINGS
block; `DEEPGRB_*` environment variables override them. At start it prints a status table of the nine steps and runs
only the missing ones.

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

Main parameters (`connections/utils/config.py`): network 60 inputs → 2048 → 2048 → 1024 → 36,
MAE loss, Nadam, 64 epochs, batch 2048; SAA mask ±150 bins around
data gaps longer than 500 s; FOCuS on rates with mu_min 1.2 and t_max 50 bins;
trigger 3σ in 50–300 keV on at least 1 detector; triggers closer than
600 s merged into one event; event significance S = Σ(N−B)/√ΣB over the triggered detectors and the
event interval, maximised over 21 quantile cuts; consistency C = max(S_r0, S_r1, S_r2); tier R (several detectors and
energy ranges), S (several detectors, one range), P (the others).

Every run writes `manifest.json` with its parameters, the model bundle (seed and sha256) and one line per execution.
A run whose parameters or bundle differ from the current ones stops instead of mixing results.

## Validation

Two references, kept separate (`docs/VALIDATION.md`):

- **the official Fermi-GBM trigger catalog** (all trigger types) and the Burst Catalog for GRB durations: what the
  pipeline finds of what Fermi already saw;
- **the tables of Crupi et al.** (Table 11, known events; Table 10, unknown events): how well the paper is reproduced.

Matching is one-to-one: a reference is matched when its time falls in the event interval extended by two bins.

## Classification

The classifier is Crupi's heuristic "manual classification logic" (thresholds read from one-vs-rest decision trees
and refined by hand): GRB, SF (solar flare), TGF, GF (galactic flare), UNC(LP) (uncertain, local particles). It uses
physical features only and never reads catalog columns. It is the baseline to be outperformed by a learned classifier.

## Scope

- Events without counterpart are candidates, not discoveries; post-processing flags mark those near the SAA or next to
  bins where the predicted background is zero.
- The localization (PSO on the cosine response of the NaI detectors) is not validated and serves as classifier input.
- The 2019 baseline and its numbers: `docs/BASELINE_2019.md`.

## Credits

DeepGRB was created by **Riccardo Crupi** and **Giuseppe Dilillo**, with Elisabetta Bissaldi, Kester Ward,
Fabrizio Fiore and Andrea Vacchi. Original repository: [github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB).

- **Searching for long faint astronomical high energy transients: a data driven approach.** Riccardo Crupi, Giuseppe
  Dilillo, Kester Ward, Elisabetta Bissaldi, Fabrizio Fiore, Andrea Vacchi. Experimental Astronomy 56, 421 (2023).
  https://link.springer.com/article/10.1007/s10686-023-09915-7
- Poisson-FOCuS: An efficient online method for detecting count bursts with application to gamma ray burst detection.
  Kester Ward, Giuseppe Dilillo, Idris Eckley, Paul Fearnhead. https://arxiv.org/abs/2208.01494

Reproducible version maintained by Giovanni Pio Martello (Politecnico di Bari). License: MIT.
