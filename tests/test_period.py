"""Tests for the explicit, inclusive analysis window (docs/WORKING_RULES.md §5.5)."""

import unittest

import pandas as pd

import ast
from pathlib import Path

import connections.utils.config as cfg
from utils.period import days_with_data, in_window, months_to_window, window_days
from utils.run_options import RunOptionsError, settings_to_env

REPO = Path(__file__).resolve().parents[1]


def user_settings() -> dict:
    """Literal assignments at the top of pipeline/pipeline_bkg.py (the USER SETTINGS block)."""
    tree = ast.parse((REPO / "pipeline" / "pipeline_bkg.py").read_text())
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper()
            and isinstance(n.value, ast.Constant)}


class TestPeriodSettings(unittest.TestCase):
    def test_user_settings_define_inclusive_baseline_window(self):
        s = user_settings()
        self.assertEqual((s["START_DATE"], s["END_DATE"]), ("2019-03-01", "2019-06-30"))

    def test_config_has_no_period(self):
        # the period lives only in USER SETTINGS / DEEPGRB_*; tools read it from the run manifest
        self.assertFalse(hasattr(cfg, "START_DATE") or hasattr(cfg, "END_DATE"))

    def test_environment_has_priority(self):
        s = {"START_DATE": "2019-03-01", "END_DATE": "2019-06-30", "RUN_LABEL": None, "FORCE_TRAIN": False, "JOBS": 4}
        env = settings_to_env(s, {"DEEPGRB_END_DATE": "2019-03-03", "DEEPGRB_RUN_LABEL": ""})
        self.assertEqual((env["DEEPGRB_START_DATE"], env["DEEPGRB_END_DATE"]), ("2019-03-01", "2019-03-03"))
        self.assertEqual((env["DEEPGRB_RUN_LABEL"], env["DEEPGRB_FORCE_TRAIN"], env["DEEPGRB_JOBS"]), ("", "", "4"))
        self.assertEqual(settings_to_env({**s, "FORCE_TRAIN": True}, {})["DEEPGRB_FORCE_TRAIN"], "1")

    def test_missing_period_is_an_error(self):
        with self.assertRaises(RunOptionsError):
            settings_to_env({"START_DATE": None, "END_DATE": "2019-06-30"}, {})


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
