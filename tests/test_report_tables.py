"""Tables of the run report (benchmark/report_tables.py) on synthetic data: percentages and joins."""

import unittest

import numpy as np
import pandas as pd

from benchmark.report_tables import (JoinError, check_gbm_join, confusion_metrics, crupi_named_list, gbm_named_list,
                                     gbm_type_vs_class)

MARGIN = 8.192
MAX_OFFSET = 204.8


def table(pairs):
    return pd.DataFrame(pairs, columns=["crupi_class", "predicted_class"])


class TestConfusion(unittest.TestCase):
    def setUp(self):
        # GRB: 3 right, 1 -> SF; SF: 1 right; TGF: 1 -> GRB; one multi-label row is excluded
        self.cm = confusion_metrics(table([("GRB", "GRB")] * 3 + [("GRB", "SF"), ("SF", "SF"), ("TGF", "GRB"),
                                                                    ("GRB/GF", "GRB")]))

    def test_counts_and_accuracy(self):
        c = self.cm["counts"]
        self.assertEqual(self.cm["n"], 6)  # the 'GRB/GF' row is not single-label
        self.assertEqual((c.loc["GRB", "GRB"], c.loc["GRB", "SF"], c.loc["TGF", "GRB"]), (3, 1, 1))
        self.assertEqual(self.cm["correct"], 4)
        self.assertAlmostEqual(self.cm["accuracy"], 400 / 6)

    def test_row_percentages_are_recall(self):
        r = self.cm["row_pct"]
        self.assertAlmostEqual(r.loc["GRB", "GRB"], 75.0)
        self.assertAlmostEqual(r.loc["GRB", "SF"], 25.0)
        np.testing.assert_allclose(r.dropna(how="all").sum(axis=1), 100.0)

    def test_column_percentages_are_precision(self):
        c = self.cm["col_pct"]
        self.assertAlmostEqual(c.loc["GRB", "GRB"], 75.0)  # 3 of the 4 predicted GRB
        self.assertAlmostEqual(c.loc["SF", "SF"], 50.0)    # 1 of the 2 predicted SF
        np.testing.assert_allclose(c.dropna(axis=1, how="all").sum(axis=0), 100.0)

    def test_per_class(self):
        p = self.cm["per_class"].set_index("classe")
        self.assertEqual(p.loc["GRB", "supporto (Crupi)"], 4)
        self.assertAlmostEqual(p.loc["GRB", "recall %"], 75.0)
        self.assertAlmostEqual(p.loc["SF", "precision %"], 50.0)
        self.assertEqual(p.loc["TGF", "predetti"], 0)
        self.assertTrue(np.isnan(p.loc["TGF", "precision %"]))  # never predicted: precision undefined


def events():
    # three events: [100, 120], [500, 510], [900, 1000]; the FOCuS change point is the event start
    return pd.DataFrame({"trig_ids": [10, 11, 12], "start_met": [100.0, 500.0, 900.0], "end_met": [120.0, 510.0, 1000.0]})


def matches(event, trig_met, dt, matched=None, types=None, has_data=None):
    n = len(event)
    return pd.DataFrame({
        "name": [f"T{i}" for i in range(n)], "trigger_name": [f"bn{i}" for i in range(n)],
        "trigger_type": types or ["GRB"] * n, "trigger_time": ["2019-03-01"] * n, "T90": [10.0] * n,
        "trig_met": trig_met, "dt_start_s": dt, "event": event,
        "matched": matched if matched is not None else [e >= 0 for e in event],
        "has_data": has_data if has_data is not None else [True] * n,
    })


class TestGbmJoin(unittest.TestCase):
    def test_correct_join_passes(self):
        check_gbm_join(matches([0, 1, 2], [105.0, 495.0, 1005.0], [5.0, -5.0, 105.0]), events(), MARGIN, MAX_OFFSET)

    def test_wrong_event_index_fails(self):
        with self.assertRaises(JoinError):  # trigger at 105 s pointing to the event [500, 510]
            check_gbm_join(matches([1], [105.0], [5.0]), events(), MARGIN, MAX_OFFSET)

    def test_outside_margin_fails(self):
        with self.assertRaises(JoinError):
            check_gbm_join(matches([0], [130.0], [30.0]), events(), MARGIN, MAX_OFFSET)  # 10 s after the end
        with self.assertRaises(JoinError):
            check_gbm_join(matches([5], [105.0], [5.0]), events(), MARGIN, MAX_OFFSET)  # index out of range

    def test_unmatched_rows_are_ignored(self):
        check_gbm_join(matches([-1], [3000.0], [np.nan]), events(), MARGIN, MAX_OFFSET)


class TestGbmTypeAndLists(unittest.TestCase):
    def setUp(self):
        self.cls = pd.DataFrame({"trig_ids": [10, 11, 12], "predicted_class": ["GRB", "SF", "UNC"]})
        self.m = matches([0, 1, 2, -1, -1], [105.0, 505.0, 950.0, 3000.0, 4000.0], [5.0, 5.0, 50.0, np.nan, np.nan],
                         types=["GRB", "SFLARE", "LOCLPAR", "GRB", "TGF"], has_data=[True, True, True, True, False])

    def test_type_vs_class_and_hypothetical_concordance(self):
        counts, row_pct, conc, total = gbm_type_vs_class(self.m, self.cls)
        self.assertEqual(int(counts.to_numpy().sum()), 3)  # only matched triggers
        self.assertEqual(counts.loc["SFLARE", "SF"], 1)
        self.assertEqual((total["agree"], total["n"]), (2, 3))  # LOCLPAR -> UNC is not UNC(LP)
        c = conc.set_index("tipo GBM")
        self.assertEqual(c.loc["LOCLPAR", "concordi"], 0)
        self.assertEqual(c.loc["LOCLPAR", "classe attesa (ipotesi)"], "UNC(LP)")
        np.testing.assert_allclose(row_pct.sum(axis=1), 100.0)

    def test_named_gbm_list(self):
        lst = gbm_named_list(self.m, events(), self.cls)
        self.assertEqual(lst["esito"].tolist(), ["rivelato", "rivelato", "rivelato", "mancato", "senza dati"])
        self.assertEqual(lst["evento_trig_ids"].tolist()[:3], [10, 11, 12])
        self.assertEqual(lst["classe_predetta"].tolist(), ["GRB", "SF", "UNC", "", ""])

    def test_named_crupi_list(self):
        ref = pd.DataFrame({"id": ["2019_1", "2019_2"], "catalog_name": ["GRB190301000", "UNKNOWN: TGF"],
                            "trigger_time_utc": ["t1", "t2"], "CE": ["R", "P"], "matched": [True, False],
                            "event": [2, -1], "diagnosis": ["", "below threshold"]})
        lst = crupi_named_list(ref.iloc[:1], ref.iloc[1:], events(), self.cls)
        self.assertEqual(lst["esito"].tolist(), ["ritrovato", "non ritrovato"])
        self.assertEqual(lst["classe_predetta"].tolist(), ["UNC", ""])
        self.assertEqual(lst["evento_trig_ids"].tolist(), [12, ""])
        self.assertEqual(lst["diagnosi"].tolist(), ["", "below threshold"])


if __name__ == "__main__":
    unittest.main()
