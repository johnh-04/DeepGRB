"""The classifier must not use catalog information (docs/WORKING_RULES.md §5.2, Phase 4)."""

import unittest

import numpy as np
import pandas as pd

from models.event_classifier import CrupiEventClassifier


def events() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    n = 40
    return pd.DataFrame({
        "trig_ids": range(n),
        "start_times": ["2019-03-01 00:00:00"] * n,
        "duration": rng.uniform(4, 300, n),
        "trig_dets": rng.choice(["n0_r0 n0_r1", "n3_r1", "n1_r0 n2_r0 n2_r1 n2_r2", "n9_r1 na_r1"], n),
        "sigma_r0": rng.uniform(0, 12, n), "sigma_r1": rng.uniform(0, 12, n), "sigma_r2": rng.uniform(0, 6, n),
        "ra": rng.uniform(0, 360, n), "dec": rng.uniform(-90, 90, n),
        "ra_earth": rng.uniform(0, 360, n), "dec_earth": rng.uniform(-90, 90, n),
        "ra_sun": rng.uniform(0, 360, n), "dec_sun": rng.uniform(-30, 30, n),
        "b_galactic": rng.uniform(-90, 90, n), "lat_fermi": rng.uniform(-26, 26, n),
        "lon_fermi": rng.uniform(0, 360, n), "l": rng.uniform(1, 1.7, n),
        "earth_vis": rng.choice([True, False], n),
    })


def predict(df: pd.DataFrame) -> pd.Series:
    clf = CrupiEventClassifier(df)
    clf.prepare_features()
    return clf.apply_classification_logic()["predicted_class"]


class TestNoLeakage(unittest.TestCase):
    def test_catalog_does_not_change_prediction(self):
        base = events()
        with_cat = base.copy()
        with_cat["catalog_triggers"] = ["GRB190301001" if i % 2 else "TGF190301002" for i in range(len(base))]
        blank_cat = base.copy()
        blank_cat["catalog_triggers"] = ""
        pd.testing.assert_series_equal(predict(with_cat), predict(base))
        pd.testing.assert_series_equal(predict(blank_cat), predict(base))

    def test_classes_are_from_the_rule_set(self):
        self.assertTrue(set(predict(events())) <= {"GRB", "TGF", "SF", "UNC(LP)", "GF", "UNC"})


if __name__ == "__main__":
    unittest.main()
