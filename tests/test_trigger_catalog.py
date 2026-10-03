"""Tests for the trigger catalog normalisation (interval semantics as upstream)."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from connections.fermi_data_tools import build_trigger_catalog, df_trigger_catalog

RAW = pd.DataFrame({
    "name": ["GRB120403857"],
    "trigger_name": ["bn120403857"],
    "trigger_type": ["GRB"],
    "time": ["2012-04-03 20:31:42.811"],
    "end_time": ["2012-04-03 20:41:57.221"],
    "trigger_time": ["2012-04-03 20:33:58.493"],
    "trigger_timescale": [1024],
    "detector_mask": ["00000000011000"],
})


class TestTriggerCatalog(unittest.TestCase):
    def test_interval_is_time_to_end_time_as_upstream(self):
        cat = build_trigger_catalog(RAW).iloc[0]
        # values from the upstream data/gbm_trig_catalog.csv
        self.assertAlmostEqual(cat.met_time, 355177904.811, places=3)
        self.assertAlmostEqual(cat.met_end_time, 355178519.221, places=3)
        self.assertAlmostEqual(cat.trig_met, 355178040.493, places=3)
        self.assertEqual(cat.detector_mask, "['n9', 'na']")

    def test_writes_file_from_given_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cat.csv"
            df_trigger_catalog(out, raw=RAW)
            self.assertEqual(pd.read_csv(out)["name"].tolist(), ["GRB120403857"])


if __name__ == "__main__":
    unittest.main()
