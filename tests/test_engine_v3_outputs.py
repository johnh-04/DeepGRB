"""Engine v3 changes only step 5 where B <= 0: on a run without zero predictions the results are identical."""

import hashlib
import json
import unittest

from connections.utils.config import DATA_DIR, END_DATE, START_DATE

RUNS = DATA_DIR / "runs" / f"{START_DATE}_{END_DATE}"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless((RUNS / "engine-v2" / "results").exists() and (RUNS / "engine-v3" / "results").exists(),
                     "engine-v2 / engine-v3 results not on disk")
class TestV3EqualsV2WithoutZeroPredictions(unittest.TestCase):
    def test_results_identical_byte_by_byte(self):
        zero = json.loads((RUNS / "engine-v3" / "manifest.json").read_text())["predicted_zero_cells"]["cells"]
        self.assertEqual(zero, 0)
        for f in ("events_table.csv", "triggers_table.csv"):
            self.assertEqual(sha(RUNS / "engine-v2" / "results" / f), sha(RUNS / "engine-v3" / "results" / f), f)


if __name__ == "__main__":
    unittest.main()
