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


class TestRulesMatchCrupi(unittest.TestCase):
    """Rule flags must equal Crupi's classification_logic (upstream script_classification2.py)."""

    def test_flags_equal_transcription(self):
        df = events()
        df["ra_std"] = np.random.default_rng(2).uniform(0, 40, len(df))
        df["dec_std"] = np.random.default_rng(3).uniform(0, 40, len(df))
        clf = CrupiEventClassifier(df)
        X = clf.prepare_features()
        y = clf.apply_classification_logic()
        ev = X["earth_vis"].astype(bool)
        expected = {
            "SF": (X["HR10"] <= 0.392) & (X["diff_sun"] < 63.49),
            "TGF": (~ev) | (X["diff_earth"] < 80),
            "GF": (X["b_galactic"].abs() < 10) & ev,
            "UNC(LP)": ((((X["dist_saa_lon"] <= 9) & (X["dist_saa_lat"] <= 3.6))
                         | ((X["dist_polo_nord_lon"] <= 19) & (X["dist_polo_nord_lat"] <= 7.6))
                         | ((X["dist_polo_sud_lon"] <= 19) & (X["dist_polo_sud_lat"] <= 7.6)))
                        & ((X["num_det"] >= 9) | (X["fe_skw"] <= 0.345))
                        # Crupi's threshold 100 applied to the variance -> 10 deg on the standard deviation
                        & ((X["diff_sun"] > 35) | (np.maximum(X["ra_std"] ** 2, X["dec_std"] ** 2) > 100))),
            "GRB": (X["HR10"] > 0.449) & (X["HR21"] <= 0.375) & (X["fe_wet"] > 2.054),
        }
        for label, exp in expected.items():
            pd.testing.assert_series_equal(y[label].astype(bool), exp.astype(bool), check_names=False, obj=label)

    def test_tgf_rule_can_fire(self):
        df = events()
        df["earth_vis"] = False
        self.assertTrue(CrupiEventClassifier(df).apply_classification_logic()["TGF"].all())
