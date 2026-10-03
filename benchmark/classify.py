"""
Phase 4: localize the events of a run and classify them with Crupi's rules (no catalog input).

Writes <run>/results/events_table_loc.csv (if missing) and <run>/results/events_classified.csv.
The validation report (python -m benchmark.validate) then compares the classes with Crupi's
tentative classes on the matched events.

Usage (from repo root): python -m benchmark.classify [--run ...] [--jobs 4] [--plots]
"""

import argparse
from pathlib import Path

import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_BKG, FOLD_POSHIST, run_dir
from models.event_classifier import CrupiEventClassifier
from models.localize_event import localize

CATALOG_COLUMNS = ["catalog_triggers"]  # kept in the output for reference, never used to classify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=run_dir())
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--plots", action="store_true", help="also save a sky map per event")
    args = parser.parse_args()
    res = args.run / "results"

    loc_path = res / "events_table_loc.csv"
    if not loc_path.exists():
        localize(res / "events_table.csv", args.run / "pred" / "frg.csv", args.run / "pred" / "bkg.csv",
                 DATA_DIR / FOLD_BKG, DATA_DIR / FOLD_POSHIST, loc_path,
                 plot_dir=res / "plots_loc" if args.plots else None, n_jobs=args.jobs)
    events = pd.read_csv(loc_path)

    features = events.drop(columns=[c for c in CATALOG_COLUMNS if c in events.columns])
    clf = CrupiEventClassifier(features)
    clf.prepare_features()
    y = clf.apply_classification_logic()
    events["predicted_class"] = y["predicted_class"].values
    events.to_csv(res / "events_classified.csv", index=False)
    print(events["predicted_class"].value_counts().to_string())


if __name__ == "__main__":
    main()
