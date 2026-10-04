# data/

Inputs, models and runs of DeepGRB. Most of it is **not versioned** (`.gitignore`): it is produced by
the pipeline or downloaded from HEASARC. Nothing here is ever deleted by the code; caches are
invalidated by moving folders to `data/_archive_<YYYYMMDD>/`.

| path | content | versioned |
|---|---|---|
| `cspec/`, `poshist/` | daily Fermi/GBM CSPEC (12 NaI + 2 BGO) and POSHIST files (step 1) | no |
| `bkg/YYMMDD.csv` | preprocessed daily tables, rates and orbital features (step 2) | no |
| `nn_model/bundles/<name>/` | model bundle: `model.keras` or `model.h5`, `scaler.joblib`, `metadata.json` (period, seed, hyper-parameters, versions, per-channel MAE) | only `metadata.json` |
| `nn_model/model_03-2019_07-2019_4.4_2026-09-21.h5` | legacy 2019 network (trained by upstream-equivalent code), wrapped into its bundle | no |
| `runs/<start>_<end>/engine-v<N>[-<label>]/` | one pipeline run: `manifest.json`, `pred/`, `trig/` (steps 3-4), `results/` (5-7), `validation/` (8), `RESULTS.md` (9), `analysis/` (orbit tools) | all but `pred/`, `trig/` |
| `gbm_trig_catalog.csv` | Fermi/GBM trigger catalog (HEASARC fermigtrig, normalised) | yes (4 MB) |
| `gbm_burst_catalog.db` | Fermi/GBM Burst Catalog (SQLite, table GBM_GRB), used for T90 | no (10 MB) |
| `DeepGRB_catalog.csv` | the 324 labelled events of Crupi et al. (2010-11, 2014, 2019) | yes |
| `_archive_<YYYYMMDD>/` | archived caches and runs, with a README and checksums | README and checksums |
| `pred/`, `trig/`, `results/`, `plots/` | outputs of the old layout (before the run folders) | no |

Rebuild the catalogs from HEASARC (network access needed):

```bash
python -c "from connections.fermi_data_tools import df_trigger_catalog, df_burst_catalog; df_trigger_catalog(); df_burst_catalog()"
```
