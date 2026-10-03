"""Tests for the background model wrapper (docs/WORKING_RULES.md §5.3, §5.7, UTC timestamps)."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from models.model_nn import COL_DET_POS, COL_SAT_POS, ModelNN, met_to_utc, saa_mask_indices
from utils.keys import get_keys

KEYS = get_keys()


def write_day(bkg_dir: Path, day: str, met0: float, n: int = 40, saa_rows=(), seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(size=(n, len(COL_SAT_POS) + len(COL_DET_POS))), columns=COL_SAT_POS + COL_DET_POS)
    df["saa"] = 0
    df.loc[list(saa_rows), "saa"] = 1
    for k in KEYS:
        df[k] = 50.0 + rng.poisson(20, size=n)
    df["met"] = met0 + 4.096 * np.arange(n)
    df.to_csv(bkg_dir / f"{day}.csv", index=False)


class TestTime(unittest.TestCase):
    def test_met_to_utc_matches_grb190303240_bin(self):
        ts = met_to_utc([573284724.164136])
        self.assertEqual(str(ts.iloc[0]), "2019-03-03 05:45:19.164136")


class TestSaaMask(unittest.TestCase):
    def test_both_sides_of_every_gap(self):
        met = np.concatenate([np.arange(0, 40) * 4.096, 1000 + np.arange(0, 40) * 4.096, 3000 + np.arange(0, 40) * 4.096])
        rows = saa_mask_indices(met, time_to_del=5)
        # gaps after rows 39 and 79: masked rows 35..44 and 75..84
        self.assertEqual(rows.tolist(), list(range(35, 45)) + list(range(75, 85)))

    def test_clipped_to_table(self):
        met = np.concatenate([np.arange(0, 3) * 4.096, 1000 + np.arange(0, 3) * 4.096])
        self.assertEqual(saa_mask_indices(met, time_to_del=10).tolist(), list(range(6)))

    def test_no_gap(self):
        self.assertEqual(len(saa_mask_indices(np.arange(100) * 4.096, 150)), 0)


class ModelTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.bkg_dir = self.root / "bkg"
        self.bkg_dir.mkdir()
        write_day(self.bkg_dir, "190228", 0.0, seed=1)  # outside window
        write_day(self.bkg_dir, "190301", 86400.0, saa_rows=(0, 1), seed=2)
        write_day(self.bkg_dir, "190302", 2 * 86400.0, seed=3)  # end day, must be included
        write_day(self.bkg_dir, "190303", 3 * 86400.0, seed=4)  # outside window
        self.cat = self.root / "trig.csv"
        pd.DataFrame({"met_time": [86400.0 + 4.096 * 10 - 1], "met_end_time": [86400.0 + 4.096 * 12 + 1]}).to_csv(self.cat, index=False)

    def tearDown(self):
        self._tmp.cleanup()

    def model(self):
        m = ModelNN("2019-03-01", "2019-03-02", bkg_dir=self.bkg_dir, trig_catalog_path=self.cat)
        m.prepare(bool_del_trig=True)
        return m


class TestPrepare(ModelTestCase):
    def test_inclusive_window_saa_and_catalog_exclusion(self):
        m = self.model()
        self.assertEqual(len(m.df_data), 40 + 40 - 2)  # two days, SAA rows dropped
        self.assertTrue(m.df_data["met"].between(86400.0, 2 * 86400.0 + 4.096 * 39).all())
        # rows 10, 11, 12 of day 190301 fall inside the cataloged trigger (rows shift by 2 after SAA drop)
        excluded = m.df_data.loc[~m.index_date, "met"].tolist()
        self.assertEqual(excluded, [86400.0 + 4.096 * i for i in (10, 11, 12)])


class TestBundleAndPredict(ModelTestCase):
    def test_train_bundle_roundtrip_and_predict(self):
        m = self.model()
        bundle = self.root / "bundle"
        meta = m.train(bundle, seed=7, units=8, epochs=2, bs=16)
        self.assertEqual(meta["seed"], 7)
        saved = json.loads((bundle / "metadata.json").read_text())
        self.assertEqual(saved["period"], {"start_date": "2019-03-01", "end_date": "2019-03-02"})
        self.assertEqual(set(saved["metrics"]), set(KEYS))
        self.assertTrue((bundle / "scaler.joblib").exists())

        m2 = ModelNN("2019-03-01", "2019-03-02", bkg_dir=self.bkg_dir, trig_catalog_path=self.cat)
        m2.prepare()
        m2.load_bundle(bundle)
        np.testing.assert_allclose(m2.scaler.mean_, m.scaler.mean_)

        # make one observed cell zero: it must become NaN in both outputs
        m2.df_data.loc[5, "n3_r2"] = 0
        frg_path, bkg_path = self.root / "out" / "frg.csv", self.root / "out" / "bkg.csv"
        m2.predict(frg_path, bkg_path, time_to_del=3)
        frg, bkg = pd.read_csv(frg_path), pd.read_csv(bkg_path)
        self.assertEqual(len(frg), len(m2.df_data))
        self.assertTrue(np.isnan(frg.at[5, "n3_r2"]) and np.isnan(bkg.at[5, "n3_r2"]))
        # gap between the two days: first row of day 2 is position 38; rows 35..40 masked, met kept
        self.assertTrue(frg.loc[35:40, KEYS].isna().all().all())
        self.assertTrue(bkg.loc[35:40, KEYS].isna().all().all())
        self.assertFalse(bkg["met"].isna().any())
        self.assertTrue(frg.loc[[0, 34, 41], KEYS].notna().all().all())

        with self.assertRaises(FileExistsError):
            m2.predict(frg_path, bkg_path)

    def test_refitted_scaler_is_deterministic(self):
        a, b = self.model(), self.model()
        np.testing.assert_array_equal(a.fit_scaler().mean_, b.fit_scaler().mean_)


if __name__ == "__main__":
    unittest.main()
