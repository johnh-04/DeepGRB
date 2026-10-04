import unittest

import numpy as np

from utils.fermi_time import met_to_utc, utc_to_met


class TestFermiTime(unittest.TestCase):
    def test_known_pair(self):
        # pair checked against gbm-data-tools (Time(..., format='fermi').utc)
        self.assertAlmostEqual(utc_to_met(["2019-03-03 05:45:19.164136"])[0], 573284724.164136, places=4)
        self.assertEqual(str(met_to_utc([573284724.164136]).iloc[0])[:23], "2019-03-03 05:45:19.164")

    def test_trigger_catalog_pair(self):
        # GRB120403857 trigger_time / trig_met from the HEASARC catalog
        self.assertAlmostEqual(utc_to_met(["2012-04-03 20:33:58.493"])[0], 355178040.493, places=3)

    def test_missing(self):
        self.assertTrue(np.isnan(utc_to_met([None, "2019-03-03 05:45:19"])[0]))



class TestSingleImplementation(unittest.TestCase):
    """One time conversion for the whole code (duplicates in model_nn and fermi_data_tools removed)."""

    def test_engine_and_catalog_use_utils_fermi_time(self):
        import connections.fermi_data_tools as fdt
        import models.model_nn as mnn
        import utils.fermi_time as ft
        self.assertIs(mnn.met_to_utc, ft.met_to_utc)
        self.assertIs(fdt.utc_to_met, ft.utc_to_met)

    def test_matches_gbm_data_tools(self):
        from gbm.time import Met
        for iso in ("2019-03-03 05:45:19.164136", "2012-04-03 20:33:58.493", "2016-12-31 23:59:59.5", "2017-01-01 00:00:01"):
            self.assertAlmostEqual(utc_to_met([iso])[0], Met(0).from_iso(iso.replace(" ", "T")).met, places=5)


if __name__ == "__main__":
    unittest.main()
