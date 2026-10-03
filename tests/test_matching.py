"""Tests for one-to-one event/reference matching (docs/WORKING_RULES.md §6, Phase 3)."""

import unittest

import numpy as np

from benchmark.matching import PRIMARY_MARGIN, match_one_to_one


class TestMatchOneToOne(unittest.TestCase):
    def test_inside_interval_and_margin(self):
        m = match_one_to_one([100, 500], [150, 520], [120, 520 + PRIMARY_MARGIN, 700])
        self.assertEqual(m["event"].tolist(), [0, 1, -1])
        self.assertEqual(m["distance"].iloc[0], 0.0)
        self.assertAlmostEqual(m["distance"].iloc[1], PRIMARY_MARGIN)

    def test_one_event_matches_at_most_one_reference(self):
        # two references inside the same event: the closer to the start wins, the other is unmatched
        m = match_one_to_one([100], [200], [150, 101])
        self.assertEqual(m["event"].tolist(), [-1, 0])

    def test_reference_prefers_inside_over_margin(self):
        m = match_one_to_one([100, 130], [120, 160], [125])
        self.assertEqual(m["event"].tolist(), [1])

    def test_conflict_resolution_keeps_both_when_possible(self):
        # ref A is inside event 0 only; ref B is inside both: B must take event 1
        m = match_one_to_one([100, 110], [130, 140], [105, 120])
        self.assertEqual(m["event"].tolist(), [0, 1])

    def test_missing_time_is_kept_unmatched(self):
        m = match_one_to_one([100], [200], [np.nan, 150])
        self.assertEqual(len(m), 2)
        self.assertEqual(m["matched"].tolist(), [False, True])

    def test_no_events(self):
        m = match_one_to_one([], [], [1.0, 2.0])
        self.assertFalse(m["matched"].any())


if __name__ == "__main__":
    unittest.main()
