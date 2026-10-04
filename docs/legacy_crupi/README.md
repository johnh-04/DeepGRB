# Legacy scripts of Crupi et al. kept for the XGBoost phase

Not part of the pipeline and not runnable as they are (paths of the original layout). Kept as reference for phase 6 (docs/WORKING_RULES.md):

- `manual_label.py`: Crupi's manual labels of the 2010-11, 2014 and 2019 events (positional; to be re-attached by time with `benchmark/matching.py`, never by position).
- `train_classifier.py`: Crupi's supervised benchmark (random forest, decision tree, L1 LinearSVC) on the labelled catalog; the reference to compare XGBoost with.
