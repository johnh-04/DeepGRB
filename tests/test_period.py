"""Tests for the explicit, inclusive analysis window (docs/WORKING_RULES.md §5.5)."""

import unittest

import pandas as pd

import connections.utils.config as cfg
from utils.period import days_with_data, in_window, months_to_window, window_days


class TestConfigWindow(unittest.TestCase):
    def test_config_defines_inclusive_crupi_window(self):
        self.assertEqual(cfg.START_DATE, "2019-03-01")
        self.assertEqual(cfg.END_DATE, "2019-06-30")


class TestWindowDays(unittest.TestCase):
    def test_both_ends_included(self):
        days = window_days("2019-03-01", "2019-07-09")
        self.assertEqual(len(days), 131)
        self.assertEqual(days[0], "190301")
        self.assertEqual(days[-1], "190709")

    def test_single_day(self):
        self.assertEqual(window_days("2019-07-09", "2019-07-09"), ["190709"])

    def test_reversed_window_raises(self):
        with self.assertRaises(ValueError):
            window_days("2019-07-10", "2019-07-09")


class TestInWindow(unittest.TestCase):
    def test_end_day_is_fully_included(self):
        times = pd.Series([
            "2019-02-28 23:59:59",  # before
            "2019-03-01 00:00:00",  # first instant
            "2019-07-09 23:59:59.9",  # last day, last second
            "2019-07-10 00:00:00",  # after
            None,  # missing time is never inside
        ])
        mask = in_window(times, "2019-03-01", "2019-07-09")
        self.assertEqual(mask.tolist(), [False, True, True, False, False])


class TestMonthsToWindow(unittest.TestCase):
    def test_legacy_end_month_is_exclusive(self):
        # Legacy labels '03-2019'..'07-2019' meant March to June included.
        self.assertEqual(months_to_window("03-2019", "07-2019"), ("2019-03-01", "2019-06-30"))


class TestDaysWithData(unittest.TestCase):
    def test_counts_only_days_inside_window(self):
        ts = pd.Series([
            "2019-02-28 10:00:00",
            "2019-03-01 00:00:01",
            "2019-03-01 12:00:00",
            "2019-06-30 23:59:00",
            None,
            "2019-07-10 01:00:00",
        ])
        self.assertEqual(days_with_data(ts, "2019-03-01", "2019-07-09"), ["2019-03-01", "2019-06-30"])


if __name__ == "__main__":
    unittest.main()
