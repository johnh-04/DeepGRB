# 2019 baseline

## Reference run

- Run: `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`; period 2019-03-01 → 2019-06-30 (UTC days, both included,
  122 days with data); engine v3.
- Network: `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1` — seed 1; 1164300 / 498987 / 554429
  rows for fit / validation / test; 64 epochs (best 57); 2048 units, lr 0.0008,
  batch 2048, dropout 0.02; mean test MAE over the 36 channels 4.383;
  6.3 min of training on /physical_device:GPU:0; versions:
  python 3.9.23, tensorflow 2.20.0, keras 3.10.0, numpy 1.26.4, pandas 1.5.3, sklearn 1.6.1.
- Bundle checksum recorded in the manifest: `0eae86f65d97b285976955b98d80a8b5df8202fb8ea9df84973958eb7bc9ee08`.
- Steps 3-4 of this run (`pred/`, `trig/`) are symbolic links to `data/runs/2019-03-01_2019-06-30/engine-v2-seed1`, computed with the same
  bundle by engine v2, whose steps 3-4 are identical to v3.
  Engine v3 changed only step 5 (bins with predicted background ≤ 0 are excluded from S).

## Results

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

GBM triggers by type:

| trigger_type | total_in_window | missing_no_data | available | detected |
|---|---|---|---|---|
| GRB | 93 | 15 | 78 | 59 |
| LOCLPAR | 7 | 4 | 3 | 3 |
| SFLARE | 5 | 0 | 5 | 5 |
| TGF | 27 | 4 | 23 | 0 |
| UNCERT | 11 | 0 | 11 | 0 |

Acceptance criteria (`docs/VALIDATION.md`):

| criterion | measured | result |
|---|---|---|
| Crupi's known events found ≥ 90% | 70/71 (98.6%) | ✔ |
| all known R and S events found | 65/65 (100.0%) | ✔ |
| unknown R+S events found ≥ 90% | 15/16 (93.8%) | ✔ |
| all unknown events found ≥ 70% | 21/24 (87.5%) | ✔ |
| GRB recall T90 > 4.096 s of the order of 88% (paper) | 54/65 (83.1%) | order of magnitude |
| GRB recall T90 ≤ 4.096 s of the order of 34% (paper) | 5/13 (38.5%) | order of magnitude |

Classification against Crupi's tentative classes (87 events with a single class; rows: Crupi, columns: predicted):

| Crupi class | GRB | SF | TGF | UNC | UNC(LP) |
|---|---|---|---|---|---|
| GRB | 68 | 0 | 0 | 1 | 1 |
| SF | 0 | 4 | 1 | 0 | 0 |
| TGF | 2 | 0 | 0 | 0 | 0 |
| UNC | 0 | 0 | 0 | 0 | 0 |
| UNC(LP) | 5 | 1 | 0 | 1 | 3 |

| class | support (Crupi) | predicted | correct | recall % | precision % |
|---|---|---|---|---|---|
| GRB | 70 | 75 | 68 | 97.1% | 90.7% |
| SF | 5 | 5 | 4 | 80.0% | 80.0% |
| TGF | 2 | 1 | 0 | 0.0% | 0.0% |
| UNC | 0 | 2 | 0 | — | 0.0% |
| UNC(LP) | 10 | 4 | 3 | 30.0% | 75.0% |

GBM trigger type against predicted class, with the hypothetical mapping GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP),
UNCERT→UNC: 62/67 (92.5%) (GRB 57/59, LOCLPAR 1/3, SFLARE 4/5). The GBM type is not the physical nature of the event.

Engine anomalies: predicted background ≤ 0 in 212 cells
(6 bins), excluded from S; events next to them flagged
`near_zero_prediction`: 6, 9. Short SAA passages not masked (data gap ≤ 500 s):
45.

The full report, with every unmatched reference and every trigger by name, is `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/RESULTS.md`.

## Checksums (sha256)

| file | sha256 |
|---|---|
| `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_table.csv` | `eb0207fb7b96acef9c677b250a3f0f00503dacb18bf8d76e6d25db7cc02ed051` |
| `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/triggers_table.csv` | `b430d5e70dc4be9fb83e79a335cc54f2beb6861ec0aa79810c73108523ffc474` |
| `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_table_loc.csv` | `0346fec93a02e9981acc9c1ce6e84031590b5665ae95ac645dfc1b1cc13fd418` |
| `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_classified.csv` | `7924b0d67c200b9e15f40a100b8c153dd84d49fe500fb4113ecf968d692b86d0` |
| `data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_flags.csv` | `338c9e45d999c0f182768beb524e4062817cab03bb596c3861a92193ccb84b76` |
| `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/metadata.json` | `84e696e028442011e696c548be9337a7915c312ac326a2fcadd4923b636feb21` |
| `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/model.keras` | `b29f1e5579cdd9d3065b918eef84fe3f7590cd39fc60fdc086abeb910b7d04c3` |
| `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/scaler.joblib` | `65820d5e57b12fe23119562e6cbf5752fefe6412f5487e6c8debf3f919d35908` |

## How to reproduce

From the repository root, with the environment of `requirements.txt`.

1. Inputs: the daily tables `data/bkg/YYMMDD.csv` of the period (steps 1-2 build them from HEASARC data:
   `python -u pipeline/pipeline_bkg.py` without `SKIP_DOWNLOAD`), the catalogs `data/gbm_trig_catalog.csv` (versioned)
   and `data/gbm_burst_catalog.db` (`python -c "from connections.fermi_data_tools import df_burst_catalog; df_burst_catalog()"`),
   the POSHIST files and the network bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/` (`model.keras`, `scaler.joblib`, `metadata.json`).
2. Status of the official run (all steps present, nothing to do):

   ```bash
   DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py --dry-run
   ```

3. Steps 3-9 from the network, in a new run folder: copy the bundle under a new label and run with that label.

   ```bash
   cp -r data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1 data/nn_model/bundles/model_2019-03-01_2019-06-30_rerun
   DEEPGRB_RUN_LABEL=rerun DEEPGRB_REUSE_BUNDLE=1 DEEPGRB_SKIP_DOWNLOAD=1 nohup python -u pipeline/pipeline_bkg.py --jobs 4 > logs/rerun.out 2>&1 &
   ```

   The files of `results/` must have the checksums above; such a rerun reproduced `pred/`, `trig/`, `results/` and
   `validation/` byte for byte.
4. A new training (`DEEPGRB_FORCE_TRAIN=1` with `DEEPGRB_TRAIN_SEED`) does not reproduce the weights bit for bit
   (TensorFlow on GPU is not deterministic): the numbers above are exact only from this bundle.
