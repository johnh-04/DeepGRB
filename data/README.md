# data/

Inputs, models and runs of DeepGRB. Only the files needed to read the 2019 baseline are versioned; everything else is
produced by the pipeline or downloaded from HEASARC and stays on disk (`.gitignore`).

| path | content | versioned |
|---|---|---|
| `cspec/`, `poshist/` | daily Fermi/GBM CSPEC (12 NaI + 2 BGO) and POSHIST files (step 1) | no |
| `bkg/YYMMDD.csv` | daily tables: rates and orbital features (step 2) | no |
| `nn_model/bundles/<name>/` | network bundle: `model.keras`, `scaler.joblib`, `metadata.json` (step 3) | only `metadata.json` of the seed1 bundle |
| `runs/<start>_<end>/engine-v<N>[-<label>]/` | one run: `manifest.json`, `pred/`, `trig/`, `results/`, `validation/`, `RESULTS.md` | the official run `runs/2019-03-01_2019-06-30/engine-v3-seed1`, except `pred/` and `trig/` |
| `gbm_trig_catalog.csv` | Fermi-GBM trigger catalog (HEASARC fermigtrig, normalised) | yes |
| `gbm_burst_catalog.db` | Fermi-GBM Burst Catalog (SQLite, table `GBM_GRB`), used for T90 | no (10 MB) |

Rebuild the catalogs from HEASARC (network access needed):

```bash
python -c "from connections.fermi_data_tools import df_trigger_catalog, df_burst_catalog; df_trigger_catalog(); df_burst_catalog()"
```
