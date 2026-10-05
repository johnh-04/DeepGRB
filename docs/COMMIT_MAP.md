# Mappa dei commit (vecchio → nuovo)

La storia del repository è stata riscritta due volte, in locale, prima della pubblicazione su `main`:

1. normalizzazione degli autori, che ha anche rimosso le firme GPG dei commit di Crupi;
2. ripulitura dei riferimenti a strumenti esterni e rinomina del documento delle regole di lavoro in `docs/WORKING_RULES.md`.

Il contenuto dei file è invariato. La tabella collega all'hash attuale gli hash citati in vecchie note e nei file generati. È ricavata da `.git/filter-repo/commit-map`, che concatena le due riscritture: la colonna "originale" contiene l'hash di prima della prima riscrittura, più l'eventuale hash intermedio.

**Hash dentro file generati.**

- Si riferiscono ai commit **precedenti** alla riscrittura e non sono stati modificati a mano: `manifest.json` e `RESULTS.md` delle run, `metadata.json` dei bundle, `summary.json` della validazione.
- Gli hash citati in `docs/` sono stati aggiornati; `docs/BASELINE_2019.md` tornerebbe agli hash vecchi se rigenerato dai manifest.
- Per tradurre un hash di questi file basta cercarlo nella colonna "originale".

## Commit del progetto (92)

| nuovo | originale | autore | data | oggetto |
|---|---|---|---|---|
| `07943a2` | `73318b9` | Giovanni Pio Martello | 2026-06-27 | Update .gitignore |
| `01bbd8c` | `0dd0549` | Giovanni Pio Martello | 2026-09-19 | run on macos - 2026 |
| `60dda11` | `4479917` | johnh-04 | 2026-09-19 | Update config paths for ReCaS |
| `e83dc07` | `8c82617` | Giovanni Pio Martello | 2026-09-19 | res rmvd |
| `52ce1c3` | `7be3dbc` | johnh-04 | 2026-09-20 | build for validation |
| `477a950` | `b0b2802` | johnh-04 | 2026-09-20 | update pipeline for training new models |
| `5d12562` | `0cd56c2` | johnh-04 | 2026-09-23 | code refactoring |
| `bf0d7a1` | `2bf1003` | johnh-04 | 2026-10-03 | Update pipeline for local execution, fix benchmark validation and apply strict data gitignore |
| `f7895aa` | `b3a2c54` | johnh-04 | 2026-10-03 | Add working brief and Crupi 2019 reference tables |
| `6637def` | `5fc4c3d` | johnh-04 | 2026-10-03 | Archive hand-written 2019 benchmark report as invalid |
| `33abd15` | `3ca8b3e` | johnh-04 | 2026-10-03 | Freeze current 2019 results with checksums |
| `d86265b` | `6100975` | johnh-04 | 2026-10-03 | Add read-only data coverage inventory for 2019 window |
| `6ce5783` | `4f02cde` | johnh-04 | 2026-10-03 | Document fork vs upstream diff and start worklog |
| `7e41318` | `5d3905f` | johnh-04 | 2026-10-03 | Add explicit inclusive analysis window (START_DATE/END_DATE) |
| `04d7234` | `c59221f` | johnh-04 | 2026-10-03 | Fix download: explicit day column, per-file retry, final check |
| `8175241` | `8b8208a` | johnh-04 | 2026-10-03 | Benchmark: use explicit window and data days for FAR |
| `fc49433` | `277cf22` | johnh-04 | 2026-10-03 | Set analysis window end to 2019-06-30 |
| `6f8c2cb` | `2987592` | johnh-04 | 2026-10-03 | Log Phase 1 results in worklog |
| `1bb79e7` | `b04ced5` | johnh-04 | 2026-10-03 | Update brief: window ends 2019-06-30, decisions on paper/code discrepancies |
| `aa4a62d` | `caf9920` | johnh-04 | 2026-10-03 | Restore upstream event construction and per-event significance |
| `18740c5` | `99e763f` | johnh-04 | 2026-10-03 | Fix background model: UTC timestamps, bundles with scaler, upstream recipe |
| `ad165d9` | `255d549` | johnh-04 | 2026-10-03 | FOCuS driver: explicit paths, read-only inputs, invalid cells as NaN |
| `3674b9f` | `3ef1b64` | johnh-04 | 2026-10-03 | Pipeline: versioned run cache, no input rewriting, parameters logged |
| `38bb236` | `1dfb652` | johnh-04 | 2026-10-03 | Trigger catalog: restore upstream interval semantics, add trigger instant |
| `36f6d0e` | `9396ddf` | johnh-04 | 2026-10-03 | Add Phase 2 engine acceptance checks; archive replaced trigger catalog |
| `e2d3aff` | `3988df9` | johnh-04 | 2026-10-03 | Classifier: remove catalog leakage and legacy validation |
| `661c3ba` | `094c793` | johnh-04 | 2026-10-03 | Localization: explicit paths, local POSHIST, std instead of variance |
| `f998032` | `2100264` | johnh-04 | 2026-10-03 | Add deterministic validation with one-to-one matching |
| `717029b` | `a3250c0` | johnh-04 | 2026-10-03 | Per-period model, period via environment, retire obsolete scripts |
| `c15bacb` | `9630906` | johnh-04 | 2026-10-03 | Phase 4: deterministic parallel localization and classify command |
| `3f76ff2` | `bfccb56` | johnh-04 | 2026-10-03 | Validation: merged-event diagnosis, per-event table for extra events, t_max sensitivity |
| `6065dab` | `2884d2b` | johnh-04 | 2026-10-03 | Baseline 2019 engine-v2 results, model bundle metadata and validation report |
| `2ebe466` | `17cd98d` | johnh-04 | 2026-10-03 | Add BASELINE guide and log Phases 3-5 |
| `8489b80` | `9e9c0a5` | johnh-04 | 2026-10-03 | Classifier: restore Crupi's TGF and UNC(LP) rules, document provenance |
| `6624331` | `8d8ee09` | johnh-04 | 2026-10-03 | Report the heuristic classifier as Crupi's baseline, per-rule metrics, XGBoost plan |
| `c15f18b` | `b28c122` | johnh-04 | 2026-10-04 | Import gbm.finder lazily: no FTP login when importing the pipeline |
| `750e7e6` | `d5d0bc7` | johnh-04 | 2026-10-04 | Training: readable stdout report and richer bundle metadata |
| `ec01caa` | `1b234d4` | johnh-04 | 2026-10-04 | Pipeline: labelled runs, forced retraining, explicit seed, skip download |
| `df67708` | `c244881` | johnh-04 | 2026-10-04 | Document labelled retraining runs |
| `62d17d0` | `c66d528` | johnh-04 | 2026-10-04 | Add orbital population analysis of events without counterpart |
| `f9005cf` | `7b8e832` | johnh-04 | 2026-10-04 | Document the learning-rate schedule question; add trivial-predictor check |
| `b11a317` | `3f93eb5` | johnh-04 | 2026-10-04 | Treat non-positive predicted background as invalid in S and localization |
| `3897f98` | `94f2a21` | johnh-04 | 2026-10-04 | Engine v3: reuse v2 predictions and triggers, record predicted zeros |
| `1a82c5d` | `722b280` | johnh-04 | 2026-10-04 | Add run comparison (event-level before/after) and shared interval matcher |
| `ca318bd` | `1e87ac1` | johnh-04 | 2026-10-04 | Test: engine v3 results equal v2 byte by byte when no prediction is zero |
| `0756c7c` | `4765d74` | johnh-04 | 2026-10-04 | Add post-processing SAA flags (columns only, event list unchanged) |
| `041f280` | `69366c5` | johnh-04 | 2026-10-04 | Validation report: model seed from bundle, informative event count, measured limits |
| `3790913` | `b50f799` | johnh-04 | 2026-10-04 | Orbit analysis: attribute zero-background bins by the S window, not a +/-60 bin margin |
| `d1441e0` | `c3246c3` | johnh-04 | 2026-10-04 | Training: non-blocking convergence check against trivial predictors |
| `e729488` | `082aeb2` | johnh-04 | 2026-10-04 | Worklog: engine v3, SAA flags, report fixes, learning-rate answer |
| `7692e0a` | `29c3139` | johnh-04 | 2026-10-04 | Diagnose the seed1 zero-prediction bins (read-only) |
| `dc46a5d` | `dcd72b0` | johnh-04 | 2026-10-04 | Add near_zero_prediction post-processing flag |
| `52a40a6` | `3d1277e` | johnh-04 | 2026-10-04 | Add BASELINE_2019 reference document (generated from files) |
| `e4675cc` | `4477ae2` | johnh-04 | 2026-10-04 | Add validation outputs of engine-v3 (legacy) and engine-v3-seed1 |
| `ca98e48` | `959dde0` | johnh-04 | 2026-10-04 | Add project map (state before consolidation) |
| `e0e8da3` | `f097be3` | johnh-04 | 2026-10-04 | Record scientific invariants before consolidation |
| `1a204a5` | `07f0774` | johnh-04 | 2026-10-04 | Remove legacy modules and scripts; move Crupi's labelling scripts to docs/legacy_crupi |
| `6cb32c9` | `3659ea9` | johnh-04 | 2026-10-04 | Single configuration and single logging setup |
| `93065fc` | `a0b8f49` | johnh-04 | 2026-10-04 | Flags become engine step 7 (models/flags.py) |
| `3c5f37f` | `ee41511` | johnh-04 | 2026-10-04 | Run options: settings with environment priority, resume of existing runs, manifest helpers |
| `14e5941` | `3872e39` | johnh-04 | 2026-10-04 | Classification becomes engine step 6 (models.event_classifier.classify_events) |
| `c1d20a6` | `3124065` | johnh-04 | 2026-10-04 | Split the validation into computation (validate.py) and report writing (report.py) |
| `f040d75` | `2876911` | johnh-04 | 2026-10-04 | Pipeline: USER SETTINGS block, status table, nine self-skipping steps |
| `6c657f9` | `8c1ba6b` | johnh-04 | 2026-10-04 | Pipeline: untracked output folders do not mark the code as modified |
| `ee74676` | `cd06495` | johnh-04 | 2026-10-04 | Keep pyswarms from reconfiguring the logging |
| `5836449` | `a5d42fd` | johnh-04 | 2026-10-04 | utils/keys.py: comments and docstrings in English |
| `6574f20` | `d7e062d` | johnh-04 | 2026-10-04 | Audit tools: same --run interface, period from the manifest, logging instead of prints |
| `f332e79` | `f677f55` | johnh-04 | 2026-10-04 | Orbit tools: --run <reference> --compare <comparison>, no run name in the code |
| `9c6fa54` | `af57763` | johnh-04 | 2026-10-04 | requirements: keep the pins of what the code imports and their dependencies |
| `e5603db` | `8f2d5a1` | johnh-04 | 2026-10-04 | .gitignore: data, models and logs out of the repository; no tracked file above 5 MB |
| `43b6535` | `b554769` | johnh-04 | 2026-10-04 | baseline_doc: --run/--compare, reads run validation folders, writes the README example block |
| `d8fa9f4` | `e39e5c6` | johnh-04 | 2026-10-04 | docs: remove PROJECT_MAP.md and BASELINE.md (fused into README, BASELINE_2019 and REFACTOR_REPORT) |
| `8ce767a` | `e07a222` | johnh-04 | 2026-10-04 | README in English for the consolidated version; credits kept; data/README.md |
| `ac820ec` | `98d3c97` | johnh-04 | 2026-10-04 | docs/WORKING_RULES.md: state after the consolidation (entry point, settings, new file names) |
| `7305b3a` | `c0b8906` | johnh-04 | 2026-10-04 | flags: --run CLI to add step-7 flags to an existing run; RUNS.md network column |
| `c977a8e` | `53e7df1` | johnh-04 | 2026-10-04 | DATA_INVENTORY regenerated with the --run interface |
| `26c2985` | `c46cf31` | johnh-04 | 2026-10-04 | orbit_analysis: histogram label from the reference run name |
| `f911a28` | `6897094` | johnh-04 | 2026-10-04 | ORBIT_ANALYSIS regenerated with the --run/--compare tools (same numbers, run names instead of roles) |
| `46b0cca` | `11aeae8` | johnh-04 | 2026-10-04 | One UTC <-> MET conversion (utils/fermi_time) for engine and catalogs |
| `3aa4acc` | `539ac13` | johnh-04 | 2026-10-04 | orbit_report: use the single md_table of benchmark/report.py |
| `544a70d` | `21e4db1` | johnh-04 | 2026-10-04 | No run name or period left in the code: baseline_doc commands from the manifests, engine_checks frg name from --old-bkg; settings errors through the logger |
| `f4560e9` | `49ae617` | johnh-04 | 2026-10-04 | RESULTS.md: one line per execution of the run (date, commit, steps to run at start) |
| `a35bd28` | `9769c98` | johnh-04 | 2026-10-04 | baseline_doc: README example counts flagged events instead of a hand-written qualifier |
| `25c1fd8` | `41418a4` | johnh-04 | 2026-10-04 | Runs of 2019: results, flags, validation and RESULTS.md of every run; v3 runs regenerated by the consolidated pipeline |
| `2465c0d` | `eb452c4` | johnh-04 | 2026-10-04 | BASELINE_2019, RUNS and the README example regenerated from the run folders |
| `a41e21d` | `d9cb62a` | johnh-04 | 2026-10-04 | REFACTOR_REPORT (final) and WORKLOG entry of the consolidation |
| `50f4e66` | `9e8e07e` | johnh-04 | 2026-10-04 | struttura progetto |
| `f86d204` | `74fea63` | Giovanni Pio Martello | 2026-10-05 | Run report: confusion matrix with percentages, GBM trigger type vs predicted class, lists by name |
| `31886f6` | `552562e` | Giovanni Pio Martello | 2026-10-05 | Add pipeline_start.py: verification run of steps 3-9 with a copied bundle and a new label |
| `dc0a2de` | `fa259d0` | Giovanni Pio Martello | 2026-10-05 | Regenerate the reports of the 2019 runs (step 9 only) and BASELINE_2019 classification text |
| `5550a45` | `68ee7b8` | Giovanni Pio Martello | 2026-10-05 | Add the verification run engine-v3-verify1 (steps 3-9 with a copy of the seed1 bundle) |
| `8643aeb` | `0f1426c` | Giovanni Pio Martello | 2026-10-05 | WORKLOG: complete run report and verification run |

## Commit di Crupi e degli altri autori originali (131)

Hanno lo stesso contenuto, lo stesso autore e lo stesso messaggio che hanno su [github.com/rcrupi/DeepGRB](https://github.com/rcrupi/DeepGRB). L'hash è cambiato solo perché la prima riscrittura ha tolto le firme GPG e aggiunto l'a capo finale ai messaggi. Nei documenti questi commit si citano con l'hash **originale**, valido upstream.

| nuovo | originale | autore | data | oggetto |
|---|---|---|---|---|
| `0e4ba8a` | (invariato) | rcrupi | 2021-10-31 | First commit. |
| `1905411` | (invariato) | rcrupi | 2022-01-16 | Put localization class in /models. Add script for creating the catalogue with localization. |
| `a2d9e97` | (invariato) | rcrupi | 2022-01-16 | Refactor folder order: one for bkg and another for analysis of GRB events. Add skeleton pipeline for bkg generation and catalogue events. |
| `f4d7b96` | (invariato) | rcrupi | 2022-01-18 | Divide download method and preprocessing (feature extraction) to build table csv per day. |
| `5550da9` | (invariato) | rcrupi | 2022-01-19 | Add parallel job option for creating the lightcurve. |
| `8dd7ee9` | (invariato) | rcrupi | 2022-01-21 | Add class model Neural Network (NN): -) prepare: load csv foreground and filter trigger event -) train: fit the model -) predict: predict bkg -) plot: draft plot for bkg and frg Add prepare and train in pipeline. |
| `264f488` | (invariato) | rcrupi | 2022-01-21 | Update plot of ModelNN. |
| `968e346` | (invariato) | rcrupi | 2022-01-23 | Add draft trigger method and 3 specific trigger algorithm: cusum, focus, paramtrig in folder 'trigs'. Add in model_nn keras_tuner for best hyperparameters. Update loss function with Median Aboslute Error and Add losses in model/util. Add average difference between target y and prediction nn. Fix nn model with last dropout layer!!! |
| `06fd55c` | (invariato) | rcrupi | 2022-01-25 | Fix in download date_tmp. |
| `9b37038` | (invariato) | rcrupi | 2022-01-28 | Add shap explainer for timestamp instances. |
| `eba0889` | (invariato) | rcrupi | 2022-02-12 | Fix figure in model.plot. |
| `0447fbb` | (invariato) | peppedilillo | 2022-02-10 | trigger run update |
| `4b11b12` | (invariato) | rcrupi | 2022-02-12 | Merge remote-tracking branch 'origin/master' |
| `f9a90ec` | (invariato) | rcrupi | 2022-02-12 | Add trigger algorithm from Giuseppe Dilillo. |
| `2d0d65c` | (invariato) | rcrupi | 2022-02-12 | Merge branch 'pep_trigger' |
| `39ca64b` | (invariato) | rcrupi | 2022-02-17 | Add method for adding triggers events (names) in the foreground file frg.csv. |
| `bbb7d00` | (invariato) | rcrupi | 2022-02-17 | Minor fix in adding trigs in frg. |
| `8a34f8b` | (invariato) | rcrupi | 2022-02-20 | Minor fix in saving csv (drop index). |
| `8c51c50` | (invariato) | rcrupi | 2022-02-20 | Minor fix in logging trigger name adding. |
| `ff7c346` | (invariato) | rcrupi | 2022-03-07 | Add script for analysing GRB as an image (time bin 0.256s, 128 energy bins). Add script to visualise background and foreground, comparison useful for paper and search events not in catalogue. |
| `771f517` | (invariato) | peppedilillo | 2022-03-13 | plot fix |
| `e4f91dc` | `0592388` | rcrupi | 2022-03-14 | Update .gitignore |
| `4a30424` | `6fc3464` | rcrupi | 2022-03-14 | Delete vcs.xml |
| `0962d93` | `9a09609` | rcrupi | 2022-03-14 | Delete modules.xml |
| `a81e8b2` | `c484395` | rcrupi | 2022-03-14 | Delete DeepGRB.iml |
| `49767f6` | `b84d208` | rcrupi | 2022-03-14 | Delete Project_Default.xml |
| `4da203b` | `a3a69b8` | rcrupi | 2022-03-14 | Delete misc.xml |
| `b78582b` | `0660797` | rcrupi | 2022-03-14 | Merge pull request #1 from peppedilillo/master |
| `4793a9f` | `b665ca1` | rcrupi | 2022-03-15 | Fix null event in 'none'. |
| `942dd32` | (invariato) | rcrupi | 2022-03-08 | Save tte as numpy files. Plot GRB091024. |
| `4e8489d` | (invariato) | rcrupi | 2022-03-08 | Save tte as numpy files. Plot GRB091024. |
| `5b42337` | (invariato) | rcrupi | 2022-03-15 | Add localization class. Start building positioning method. To be substituted with "update_cataloge". Add autoencoder for GRB images. |
| `c9d8e33` | (invariato) | rcrupi | 2022-03-22 | Update loss_median with library found in the Tensorflow code. Update MAE valutation of the test and train set. Add filter zeros for training and in prediction are set to NaN. Add option Huber loss. Update plot with bkg, frg and residual. |
| `d0e62c8` | (invariato) | rcrupi | 2022-03-23 | Fix bug for deleting zero counts rate. |
| `3dfc8cc` | (invariato) | rcrupi | 2022-04-03 | Add logger for day csv loading. Set dropout as parameter. Set mc as option, defalut is True. Add median metrics in model performance. Improve plots with sns.plotting_context. |
| `11fb40a` | (invariato) | rcrupi | 2022-06-12 | In the plot of the model is added the orbit binning. Add script for paper images plot. |
| `e29c780` | `286555e` | rcrupi | 2022-06-12 | Merge pull request #2 from rcrupi/ric_GRB091024 |
| `5c641ba` | `2a69f83` | rcrupi | 2022-09-11 | Create README.md |
| `c90b26c` | `7e46ec2` | rcrupi | 2022-09-11 | Update README.md |
| `1e83a64` | `74c40a7` | rcrupi | 2022-09-13 | Create LICENSE |
| `8bf9f7b` | `c17459a` | peppedilillo | 2022-10-06 | added analyze module |
| `7dba525` | `5c9cb1a` | peppedilillo | 2022-10-07 | minors |
| `4278d33` | `9b36bd0` | peppedilillo | 2022-10-07 | added events plots |
| `6315b1e` | `51b227f` | peppedilillo | 2022-10-07 | minor. changed range untriggered plots |
| `681f5a2` | `bba17c4` | rcrupi | 2022-10-09 | Merge pull request #4 from peppedilillo/analysis |
| `f9dba62` | `4c6d051` | rcrupi | 2022-10-11 | In fermi_data_tools added update method for GRB and TRIGGER catalogs. Updated TRIG and GRB catalogs. Add try excpet in analyze. Add feature in nn.plot, now it is possible to specify the datetime. Delete zeros in frg and gkb because using trigger alg. |
| `4928569` | `6cb4795` | rcrupi | 2022-10-24 | Change T90 and flux insted of fluence. |
| `1afde18` | `171d7d4` | rcrupi | 2022-10-24 | Delete temporary code. |
| `6b4b78d` | `e4c41d8` | rcrupi | 2022-11-15 | Merge pull request #5 from rcrupi/ric_false_positive_20221011 |
| `c027b27` | `339e1c1` | rcrupi | 2022-11-16 | Delete temporary code. |
| `ac3f2bb` | `2b8b550` | rcrupi | 2022-11-16 | Merge branch 'ric_false_positive_20221011' |
| `bdc7c97` | `05da133` | rcrupi | 2022-11-19 | Reduce triggers table into events table. |
| `6800119` | `74f44ce` | rcrupi | 2022-11-20 | Reduce triggers table into events table. |
| `5d265d0` | `3dadc4d` | rcrupi | 2022-11-20 | Fix name events so the plots are with the correct index. |
| `5187bf9` | `c5def71` | rcrupi | 2022-11-27 | Restore original pipeline and add new one for experiments. |
| `b0ad1d5` | `c69f70d` | peppedilillo | 2022-11-29 | trigger condition is now consisted between redgreen and fetch_triggers. added some tests. added utilities to plot grbs in catalog and save data. |
| `c16ae48` | `bdb5309` | peppedilillo | 2022-11-29 | fixed merger. changed trigger condition to only trigger on r1 |
| `4b5fa8d` | `8b8501a` | rcrupi | 2022-11-30 | Merge pull request #6 from peppedilillo/master |
| `d6a4a78` | `8afd88e` | peppedilillo | 2022-11-30 | some documentation. fixed a bug with plot legends. |
| `702f3f8` | `0a5ebc8` | rcrupi | 2022-11-30 | Merge pull request #7 from peppedilillo/master |
| `73c7075` | `67e560a` | rcrupi | 2022-12-17 | Update plot (image) red green GRB. Update NN model name and path. Update pipeline background. |
| `931b31e` | `59688c6` | rcrupi | 2022-12-21 | Add automatic localization method. |
| `1625a34` | `5432f96` | rcrupi | 2022-12-26 | Localization small fix. |
| `161da4a` | `85542b5` | rcrupi | 2023-01-14 | In download CSPEC are deleted the files that are going to be downdloaded. This is because overwriting it the size file increase (and the file is ruined). In NN add batch normalization layer, update b1=0.9 and b2=0.99 of Nadam and regulate learning rate with a scheduler piecewise. Fix preprocessing step, now the CSPEC is first binned in energy and then in time. Add a warning if the dimension data for a day CSPEC are different among detectors. |
| `4607a2a` | `8056f48` | rcrupi | 2023-01-30 | Add a plot method for computing a proxy for fluence, flux and duration of the events. |
| `c9cc09a` | `d683a02` | rcrupi | 2023-02-18 | Add a significance of the triggers and the events in the catalog. |
| `d453814` | `1d08239` | rcrupi | 2023-03-28 | Update README.md |
| `7bb6daa` | `72943f5` | rcrupi | 2023-03-29 | Update README.md |
| `2b53e06` | `6851607` | rcrupi | 2022-11-30 | Fix images and requirements |
| `a3c45a1` | `70edb42` | rcrupi | 2022-11-30 | Merge remote-tracking branch 'origin/master' |
| `184c49f` | `ebe4f34` | rcrupi | 2023-02-19 | Merge remote-tracking branch 'origin/master' |
| `cc56e84` | `611cae2` | rcrupi | 2023-02-19 | Small fix for y limit in plot and force to be in the terminal with 'agg'. |
| `5bb71c4` | `3e6bded` | rcrupi | 2023-02-20 | Add scripts for significance analysis of the events. |
| `02181e4` | `70d67ce` | rcrupi | 2023-02-20 | Add scripts for significance analysis of the events. |
| `85a3e56` | `78ee1e9` | rcrupi | 2023-02-22 | Add durations, fix buf for standard score and limit it to 100 for latex table. |
| `b23f47e` | `9abcfe1` | rcrupi | 2023-02-24 | Add scripts for significance analysis of the events. |
| `d4d5a00` | `9bef13a` | rcrupi | 2023-02-26 | Update script latex to limit sigma to 10. Add trigger time of interesting events. Add option to avoid saving plots and data from the trigger analysis. Analyze.py: 1) Add Median Absolute Deviation (MAD) to estimate the variance of residual for each detector_range. 2) Add option 'sigma_type' to estimate the significance of the events:     2.a) Use focus sigma.     2.b) Use standard score and the Poisson hypothesis. Cut the events with different quantiles to get the interval with highest counts.     2.c) Use standard score but with MAD as standard deviation (denominator). 3) Update the events adding the offset information and saving in file csv. The Segmnet class now have more data (so it is possibile to compute better significance). In the plot the highlighted triggered part is extended on the left. start_offset=start + offset_ev + 1 and end_offset = end - 1. |
| `3f10c8a` | `1589198` | rcrupi | 2023-02-26 | Update logic for computing the significance, involving the detectors from Focus or the k highest residual. |
| `bfa6c93` | `6459898` | rcrupi | 2023-02-27 | Add new logic for computing the significance, uses focus maximum significance and goes 'offset' steps behind. |
| `e242062` | `9199e4b` | rcrupi | 2023-03-03 | Add catalog type event. |
| `11d23e8` | `f97bbad` | rcrupi | 2023-03-25 | Update green-red plot with "no data" instead of "missing". |
| `e9a3261` | `1093b98` | rcrupi | 2023-03-14 | Update unknown event class type. |
| `52a5e00` | `c5cb9fd` | rcrupi | 2023-03-14 | Update unknown event class type not solar flare. |
| `c32bde8` | `d5f5bd5` | rcrupi | 2023-03-15 | Update unknown two event class type. |
| `976d69d` | `d3b79bf` | rcrupi | 2023-03-25 | Merge remote-tracking branch 'origin/local_run_20230219' into local_run_20230219 |
| `8fa616c` | `9385fb9` | rcrupi | 2023-03-29 | Merge pull request #9 from rcrupi/local_run_20230219 |
| `76c8696` | `fb6d6de` | rcrupi | 2023-03-29 | Update README.md |
| `d0e99ed` | `f150761` | rcrupi | 2023-03-29 | Update README.md |
| `1ea0ab0` | `476afef` | rcrupi | 2023-03-29 | Update README.md |
| `81ed4ba` | `03bdf4d` | rcrupi | 2023-03-29 | Update README.md |
| `dbeb838` | `c2a2cdd` | rcrupi | 2023-03-29 | Update README.md |
| `0324ca6` | `607e6d7` | rcrupi | 2023-03-29 | Update README.md |
| `26edad3` | `ea6c2d2` | rcrupi | 2023-03-29 | Update README.md |
| `d849d9b` | `b0b3de0` | rcrupi | 2023-03-29 | Update README.md |
| `7bce2da` | `684d6db` | rcrupi | 2023-03-29 | Update README.md |
| `c9e8e4f` | `6a6ad11` | rcrupi | 2023-03-29 | Update README.md |
| `1ca62fe` | `21d3bde` | rcrupi | 2023-03-30 | Update README.md |
| `4de604b` | `9615263` | rcrupi | 2023-04-30 | Update README.md |
| `7670384` | `2130dac` | rcrupi | 2023-04-30 | Update README.md |
| `ddd1318` | `316ed00` | rcrupi | 2023-04-12 | Add information into the catalog to estimate the transient class. |
| `10e777e` | `6b97d3a` | rcrupi | 2023-04-16 | Fix bug for sun localization in the catalog. |
| `ccc5a66` | `cb3d8f9` | rcrupi | 2023-04-17 | Add logic for classification event based on localisation and other information. |
| `924bd85` | `43aaa8f` | rcrupi | 2023-04-17 | Script to download TTE of the event catalog and prepare those for further analysis (for example microvariability). |
| `4093481` | `2639163` | rcrupi | 2023-04-17 | Cycle for events, estimate background and take residual. |
| `57c81bc` | `6ea8f87` | rcrupi | 2023-04-24 | Add catalog of the three years (2010/2011, 2014, 2019) in csv in the data folder. Add mcilwain_l parameter in the catalog. Add script for analyse the events UNKNOWN and fine tune a classification rule. |
| `9f23429` | `ea1f655` | rcrupi | 2023-04-26 | Load mcilwain_l parameter in the catalog classification script. |
| `5ce5219` | `0f7f7df` | rcrupi | 2023-05-01 | Find the rule for the 6 events ['SF', 'UNC(LP)', 'TGF', 'GF', 'GRB', 'UNC']. |
| `5e7e54e` | `f9f51fc` | rcrupi | 2023-05-02 | Add logic for local particle. |
| `d16e29d` | `e930f58` | rcrupi | 2023-05-16 | Update logic for local particle. |
| `8ad8e67` | `a4aebfc` | rcrupi | 2023-05-16 | Merge pull request #10 from rcrupi/ric_class_events_20230412 |
| `578c5e1` | `10ad84c` | rcrupi | 2023-08-24 | Small fix and add two scratch scripts for MAE statistics and converting a GRB image into a lightcurve. |
| `ba95257` | `af365ea` | rcrupi | 2023-08-26 | Update script_classification2.py |
| `f795de2` | `01aad21` | rcrupi | 2023-08-26 | Improve logic for classification of SF, GRB and LP. |
| `70a5077` | `3f1495f` | rcrupi | 2023-08-28 | Update script_classification2.py |
| `442f135` | `34723b3` | rcrupi | 2023-08-30 | Improve logic for LP and simplify for GRB. |
| `63def89` | `215a8ae` | rcrupi | 2023-08-30 | Add Random Forest feature importance. |
| `9b6844a` | `2413395` | rcrupi | 2023-09-03 | Update catalog with UNC(LP) and other transients. Events: 2010 (6, 10, 14, 34), 2014 (51, 57, 61, 67, 70, 73, 127, 149, 151, 157, 177). Update catalog with DeepGRB_catalog.csv. |
| `1658d10` | `8a31bad` | rcrupi | 2023-09-03 | Minor update catalog, insert significance limit for DeepGRB catalog. |
| `1f0b2ba` | `e782abd` | rcrupi | 2023-09-03 | Minor update catalog. |
| `28c58fd` | `6afec94` | Giuseppe "Peppe" Dilillo | 2023-08-31 | Update README.md |
| `5e6faaf` | `f7ca221` | rcrupi | 2023-09-03 | Merge remote-tracking branch 'origin/master' |
| `d380e29` | `1b4f494` | rcrupi | 2023-09-03 | Change logic for GRB (now bias). |
| `3cd6e1f` | `622a165` | rcrupi | 2023-09-17 | Change logic for GRB (now bias). |
| `607f3e5` | `3af5523` | rcrupi | 2023-09-18 | Add False Positive class event. |
| `0269845` | `8f24daa` | rcrupi | 2023-09-19 | Update GRB logic and initial feature selection. |
| `1cf2ef3` | `fc799a9` | rcrupi | 2023-09-20 | Add random forest multiclass, add Anchor explainer, compute confusion matrix and performance RF 1 vs all. |
| `ed408bc` | `c3bc9a6` | rcrupi | 2023-09-24 | Add random forest multiclass, add Anchor explainer, compute confusion matrix and performance RF 1 vs all. |
| `a4a879c` | `196637e` | rcrupi | 2023-09-25 | Update log and index to explain with Anchor. |
| `3cca894` | `455084d` | rcrupi | 2023-09-27 | Add train set confusion matrix. |
| `bb13970` | `aa642cd` | rcrupi | 2023-09-27 | Update README.md |
| `18bfe63` | `0d7d82c` | rcrupi | 2023-12-12 | Update README.md |
