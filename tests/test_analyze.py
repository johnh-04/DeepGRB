"""Tests for event construction and per-event significance (docs/WORKING_RULES.md §5.1)."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from models.analyze import (
    BINLENGTH,
    EventAnalyzer,
    Segment,
    confidence_tier,
    event_significance,
    fetch_triggers,
    merge,
)
from utils.keys import get_keys

KEYS = get_keys()
REF_DIR = Path(__file__).resolve().parents[1] / "benchmark" / "reference"


def make_inputs(n=60, base=100.0):
    """Flat frg = bkg = base on all 36 channels, regular 4.096 s bins."""
    met = 1000.0 + BINLENGTH * np.arange(n)
    ts = pd.to_datetime("2019-03-01") + pd.to_timedelta(met - met[0], unit="s")
    frg = pd.DataFrame(base, index=range(n), columns=KEYS)
    bkg = frg.copy()
    for df in (frg, bkg):
        df["met"] = met
        df["timestamp"] = ts.astype(str)
    focus = pd.DataFrame(0.0, index=range(n), columns=KEYS)
    offset = pd.DataFrame(0.0, index=range(n), columns=KEYS)
    return frg, bkg, focus, offset


class TestMerge(unittest.TestCase):
    data_a = [(1, 4), (5, 9), (10, 11), (12, 13), (20, 24), (25, 26)]

    def test_upstream_examples(self):
        self.assertEqual(merge(self.data_a, 10), [(1, 9), (10, 13), (20, 26)])
        self.assertEqual(merge(self.data_a, 3), self.data_a)
        self.assertEqual(merge(self.data_a, 4), [(1, 4), (5, 9), (10, 13), (20, 24), (25, 26)])
        self.assertEqual(merge(self.data_a, 666), [(1, 26)])
        self.assertEqual(merge([(32, 56), (57, 58), (60, 64), (99, 100)], 10), [(32, 56), (57, 64), (99, 100)])

    def test_empty(self):
        self.assertEqual(merge([], 10), [])


class TestFetchTriggers(unittest.TestCase):
    def setUp(self):
        self.focus = pd.DataFrame(0.0, index=range(20), columns=KEYS)

    def test_only_range_r1_triggers(self):
        self.focus.loc[3:5, "n0_r0"] = 10.0
        self.focus.loc[3:5, "n0_r2"] = 10.0
        self.assertEqual(fetch_triggers(self.focus, 3.0), [])

    def test_end_is_one_past_last_bin(self):
        self.focus.loc[10:12, "n4_r1"] = 5.0
        self.assertEqual(fetch_triggers(self.focus, 3.0), [(10, 13)])

    def test_min_detectors(self):
        self.focus.loc[2:3, "n1_r1"] = 5.0
        self.focus.loc[3:4, "n2_r1"] = 5.0
        self.assertEqual(fetch_triggers(self.focus, 3.0, min_dets_num=2), [(3, 4)])

    def test_nan_breaks_segment(self):
        self.focus.loc[0:10, "n0_r1"] = 5.0
        self.focus.loc[4, "n0_r1"] = np.nan
        self.assertEqual(fetch_triggers(self.focus, 3.0), [(0, 4), (5, 11)])


class TestSegment(unittest.TestCase):
    def test_start_extended_by_most_negative_offset(self):
        _, _, _, offset = make_inputs()
        offset.loc[20, "n3_r1"] = -6
        offset.loc[20, "n5_r0"] = -2
        seg = Segment.from_limits(20, 25, offset)
        self.assertEqual((seg.start, seg.end, seg.start_offset, seg.end_offset), (20, 25, 15, 24))

    def test_offset_never_before_zero(self):
        _, _, _, offset = make_inputs()
        offset.loc[2, "n0_r1"] = -10
        self.assertEqual(Segment.from_limits(2, 4, offset).start_offset, 0)


class TestEventSignificance(unittest.TestCase):
    def test_hand_computed_value(self):
        frg = pd.DataFrame({"a": [110.0, 130.0, 100.0], "b": [100.0, 100.0, 100.0]})
        bkg = pd.DataFrame({"a": [100.0, 100.0, 100.0], "b": [100.0, 100.0, 100.0]})
        # summed residuals per bin: 10, 30, 0; best cut keeps the bins >= q-quantile
        # q=0: (40)/sqrt(600)=1.633; cut keeping {10,30}: 40/sqrt(400)=2.0; keeping {30}: 30/sqrt(200)=2.121
        s, q = event_significance(frg, bkg, ["a", "b"])
        self.assertAlmostEqual(s, 30 / np.sqrt(200))
        self.assertGreater(q, 0.5)

    def test_no_excess_gives_zero(self):
        frg = pd.DataFrame({"a": [90.0, 95.0]})
        bkg = pd.DataFrame({"a": [100.0, 100.0]})
        self.assertEqual(event_significance(frg, bkg, ["a"]), (0.0, 0.0))

    def test_zero_background_bins_are_ignored(self):
        # B = 0 in one bin (network output at zero): that bin must not enter S
        frg = pd.DataFrame({"a": [500.0, 130.0], "b": [500.0, 100.0]})
        bkg = pd.DataFrame({"a": [0.0, 100.0], "b": [100.0, 100.0]})
        s, _ = event_significance(frg, bkg, ["a", "b"])
        self.assertAlmostEqual(s, 30 / np.sqrt(200))

    def test_negative_background_bins_are_ignored(self):
        frg = pd.DataFrame({"a": [120.0, 130.0]})
        bkg = pd.DataFrame({"a": [-5.0, 100.0]})
        s, _ = event_significance(frg, bkg, ["a"])
        self.assertAlmostEqual(s, 30 / np.sqrt(100))

    def test_missing_bins_are_ignored(self):
        frg = pd.DataFrame({"a": [np.nan, 130.0]})
        bkg = pd.DataFrame({"a": [100.0, 100.0]})
        s, _ = event_significance(frg, bkg, ["a"])
        self.assertAlmostEqual(s, 30 / np.sqrt(100))


class TestConfidenceTier(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(confidence_tier({"r0": 4, "r1": 5, "r2": 0}, ["n0", "n1"]), "R")
        self.assertEqual(confidence_tier({"r0": 0, "r1": 5, "r2": 0}, ["n0", "n1"]), "S")
        self.assertEqual(confidence_tier({"r0": 4, "r1": 5, "r2": 3}, ["n0"]), "P")

    def test_matches_crupi_reference_tables(self):
        ref = pd.concat([pd.read_csv(REF_DIR / f"crupi_2019_{k}.csv") for k in ("known", "unknown")])

        def to_float(v):
            return 11.0 if str(v).strip() == ">10" else float(v)

        calc = ref.apply(
            lambda r: confidence_tier(
                {rng: to_float(r[f"S_{rng}"]) for rng in ("r0", "r1", "r2")}, str(r["detectors"]).split()
            ),
            axis=1,
        )
        self.assertEqual((calc == ref["CE"]).sum(), len(ref))


class TestEventAnalyzer(unittest.TestCase):
    def run_analyzer(self, frg, bkg, focus, offset, catalog=None, threshold=3.0):
        catalog = catalog if catalog is not None else pd.DataFrame(columns=["name", "met_time", "met_end_time"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            paths = {}
            for name, df in (("frg", frg), ("bkg", bkg), ("trig", focus), ("offset", offset), ("cat", catalog)):
                paths[name] = tmp / f"{name}.csv"
                df.to_csv(paths[name], index=False)
            analyzer = EventAnalyzer(paths["frg"], paths["bkg"], paths["trig"], paths["offset"], paths["cat"])
            return analyzer.run(threshold, tmp / "out")

    def test_event_row(self):
        frg, bkg, focus, offset = make_inputs()
        # excess on n2 and n3, ranges r0 and r1, bins 30..32
        for ch in ("n2_r0", "n2_r1", "n3_r0", "n3_r1"):
            frg.loc[30:32, ch] = 140.0
            focus.loc[30:32, ch] = 6.0
        offset.loc[30, "n2_r1"] = -2  # change point one bin earlier -> start_offset = 29
        catalog = pd.DataFrame({"name": ["GRB190301001"], "met_time": [frg.at[31, "met"] - 1],
                                "met_end_time": [frg.at[31, "met"] + 1]})
        triggers, events = self.run_analyzer(frg, bkg, focus, offset, catalog)
        self.assertEqual(len(triggers), 1)
        ev = events.iloc[0]
        self.assertEqual((ev.start_index, ev.end_index), (30, 33))
        self.assertAlmostEqual(ev.duration, 3 * BINLENGTH, places=6)
        self.assertEqual(ev.trig_dets, "n2_r0 n2_r1 n3_r0 n3_r1")
        self.assertEqual(ev.detectors, "n2 n3")
        # offset window = bins 29..32: residuals 0, 80, 80, 80 over 2 channels
        expected = 240.0 / np.sqrt(600.0)
        self.assertAlmostEqual(ev.sigma_r0, expected)
        self.assertAlmostEqual(ev.sigma_r1, expected)
        self.assertEqual(ev.sigma_r2, 0.0)
        self.assertAlmostEqual(ev.sigma_C, expected)
        self.assertEqual(ev.CE, "R")
        self.assertEqual(ev.catalog_triggers, "GRB190301001")

    def test_sigma_recomputed_by_hand_from_frg_bkg(self):
        frg, bkg, focus, offset = make_inputs()
        rng = np.random.default_rng(0)
        frg.loc[:, KEYS] = rng.poisson(100, size=(len(frg), len(KEYS))).astype(float)
        frg.loc[10:13, "n7_r1"] += 60.0
        focus.loc[10:13, "n7_r1"] = 5.0
        # FOCuS offset is <= -1 on a triggered bin (-1: change point at the current bin)
        offset.loc[10:13, "n7_r1"] = -1
        _, events = self.run_analyzer(frg, bkg, focus, offset)
        ev = events.iloc[0]
        diff = frg.loc[10:13, "n7_r1"].to_numpy() - 100.0
        best = max(
            diff[diff >= np.quantile(diff, q)].sum() / np.sqrt(100.0 * (diff >= np.quantile(diff, q)).sum())
            for q in np.arange(0, 21) / 20
        )
        self.assertAlmostEqual(ev.sigma_r1, max(best, 0.0))
        self.assertEqual(ev.CE, "P")

    def test_triggers_within_600s_merge_into_one_event(self):
        frg, bkg, focus, offset = make_inputs(n=200)
        focus.loc[10:11, "n0_r1"] = 5.0
        focus.loc[60:61, "n0_r1"] = 5.0  # 50 bins later (< 146 bins)
        focus.loc[190:191, "n0_r1"] = 5.0  # 180 bins after the first: separate event
        triggers, events = self.run_analyzer(frg, bkg, focus, offset)
        self.assertEqual(len(triggers), 3)
        self.assertEqual(list(zip(events.start_index, events.end_index)), [(10, 62), (190, 192)])


if __name__ == "__main__":
    unittest.main()
