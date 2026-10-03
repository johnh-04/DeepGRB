"""Tests for the FOCuS driver: NaN reach FOCuS, inputs are never rewritten (docs/WORKING_RULES.md §5.3)."""

import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from models.trigger import focus_inputs, run_trigger
from models.trigs.focus import build_focus_runner
from utils.keys import get_keys

KEYS = get_keys()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestFocusInputs(unittest.TestCase):
    def test_invalid_cells_become_nan_background(self):
        x = pd.Series([10.0, np.nan, 0.0, 12.0, 11.0])
        b = pd.Series([10.0, 10.0, 10.0, np.nan, 0.0])
        _, bb = focus_inputs(x, b)
        self.assertEqual(np.isnan(bb).tolist(), [False, True, True, True, True])


class TestRunTrigger(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        n = 60
        rng = np.random.default_rng(3)
        frg = pd.DataFrame(rng.poisson(100, size=(n, len(KEYS))).astype(float), columns=KEYS)
        bkg = pd.DataFrame(100.0, index=range(n), columns=KEYS)
        frg.loc[20:24, "n5_r1"] += 80.0  # a burst
        frg.loc[40:44, KEYS] = np.nan  # SAA edge mask
        bkg.loc[40:44, KEYS] = np.nan
        for df in (frg, bkg):
            df["met"] = 4.096 * np.arange(n)
            df["timestamp"] = "2019-03-01"
        self.frg_path, self.bkg_path = self.root / "frg.csv", self.root / "bkg.csv"
        frg.to_csv(self.frg_path, index=False)
        bkg.to_csv(self.bkg_path, index=False)

    def tearDown(self):
        self._tmp.cleanup()

    def test_nan_reset_and_inputs_untouched(self):
        before = (sha(self.frg_path), sha(self.bkg_path))
        trig_path, off_path = self.root / "trig" / "trig.csv", self.root / "trig" / "offset.csv"
        res = run_trigger(self.frg_path, self.bkg_path, trig_path, off_path, build_focus_runner(mu_min=1.2, t_max=50), n_jobs=1)
        self.assertEqual((sha(self.frg_path), sha(self.bkg_path)), before)
        self.assertTrue(res.loc[40:44].isna().all().all())
        self.assertTrue(res.drop(index=range(40, 45)).notna().all().all())
        self.assertGreater(res.loc[20:24, "n5_r1"].max(), 5.0)
        with self.assertRaises(FileExistsError):
            run_trigger(self.frg_path, self.bkg_path, trig_path, off_path, build_focus_runner(mu_min=1.2, t_max=50), n_jobs=1)

    def test_parallel_equals_serial(self):
        runner = build_focus_runner(mu_min=1.2, t_max=50)
        a = run_trigger(self.frg_path, self.bkg_path, self.root / "a.csv", self.root / "ao.csv", runner, n_jobs=1)
        b = run_trigger(self.frg_path, self.bkg_path, self.root / "b.csv", self.root / "bo.csv", runner, n_jobs=4)
        pd.testing.assert_frame_equal(a, b)


if __name__ == "__main__":
    unittest.main()
