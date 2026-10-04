"""Post-processing SAA flags (models/saa_flags.py)."""

import unittest

import numpy as np

from models.saa_flags import EDGE_WINDOW_S, PoshistTrack, compute_saa_flags, saa_passages, unmasked_passages


def track(t, lat, lon, saa) -> PoshistTrack:
    tr = PoshistTrack.__new__(PoshistTrack)
    tr.t, tr.lat, tr.lon, tr.saa = np.asarray(t, float), np.asarray(lat, float), np.asarray(lon, float), np.asarray(saa, bool)
    return tr


class TestPassages(unittest.TestCase):
    def test_entries_and_exits(self):
        t = np.arange(10.0)
        saa = np.array([0, 0, 1, 1, 0, 0, 0, 1, 1, 1])
        np.testing.assert_array_equal(saa_passages(t, saa), [[2, 4], [7, 9]])

    def test_only_unmasked_short_gaps(self):
        frg = np.r_[np.arange(0, 1000, 4.096), np.arange(1300, 3000, 4.096), np.arange(4000, 6000, 4.096)]
        passages = np.array([[1005.0, 1290.0], [3005.0, 3990.0]])  # data gaps ~304 s (unmasked) and ~1000 s (masked)
        np.testing.assert_array_equal(unmasked_passages(passages, frg), [[1005.0, 1290.0]])


class TestFlags(unittest.TestCase):
    def setUp(self):
        t = np.arange(0.0, 6000.0)
        lat = np.full_like(t, -12.0)
        lon = np.linspace(-120.0, 0.0, len(t))
        saa = (t >= 1005) & (t < 1290) | (t >= 3005) & (t < 3990)
        self.track = track(t, lat, lon, saa)
        self.frg = np.r_[np.arange(0, 1000, 4.096), np.arange(1300, 3000, 4.096), np.arange(4000, 6000, 4.096)]

    def test_edge_flag_only_near_unmasked_passage(self):
        f = compute_saa_flags([1005 - 100, 1290 + 150, 3005 - 100, 1005 - EDGE_WINDOW_S - 50], self.track, self.frg)
        self.assertEqual(f["saa_edge_short_passage"].tolist(), [True, True, False, False])
        self.assertAlmostEqual(f["saa_edge_dt_s"].iloc[0], 100.0)

    def test_region_proximity(self):
        f = compute_saa_flags([1100.0, 100.0, 5900.0], self.track, self.frg)
        self.assertTrue(f["saa_region_proximity"].iloc[0])   # inside the flagged region
        self.assertLess(f["saa_region_dist_deg"].iloc[0], 0.2)
        self.assertFalse(f["saa_region_proximity"].iloc[1])  # far west of it


if __name__ == "__main__":
    unittest.main()
