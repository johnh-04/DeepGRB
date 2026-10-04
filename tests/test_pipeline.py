"""Pipeline entry point: settings from USER SETTINGS / environment, status table, dry run writes nothing."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from connections.utils.config import DATA_DIR, LOGS_DIR, LEGACY_PERIOD, run_dir

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


def run_pipeline(*args, **env):
    full = {k: v for k, v in os.environ.items() if not k.startswith("DEEPGRB_")}
    full.update(env)
    return subprocess.run([PY, "-u", "pipeline/pipeline_bkg.py", *args], cwd=REPO, env=full,
                          capture_output=True, text=True, timeout=600)


@unittest.skipUnless((DATA_DIR / "bkg").exists(), "production data folder not available")
class TestDryRun(unittest.TestCase):
    def test_short_fictitious_period_only_needs_settings(self):
        start, end = "2019-03-02", "2019-03-03"  # no run exists for this period
        target = run_dir(start, end)
        self.assertFalse(target.parent.exists())
        logs_before = set(LOGS_DIR.glob("*")) if LOGS_DIR.exists() else set()
        p = run_pipeline("--dry-run", DEEPGRB_START_DATE=start, DEEPGRB_END_DATE=end, DEEPGRB_SKIP_DOWNLOAD="1")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(f"DEEPGRB PIPELINE  {start} -> {end}  (2 days", p.stdout)
        self.assertIn(f"run folder : {target.relative_to(REPO)}", p.stdout)
        self.assertIn("Steps to run: 3, 4, 5, 6, 7, 8, 9", p.stdout)
        self.assertIn("Dry run: nothing executed, nothing written.", p.stdout)
        self.assertFalse(target.parent.exists())  # nothing written
        self.assertEqual(set(LOGS_DIR.glob("*")) if LOGS_DIR.exists() else set(), logs_before)

    def test_force_train_without_seed_stops_before_anything(self):
        p = run_pipeline("--dry-run", DEEPGRB_START_DATE="2019-03-02", DEEPGRB_END_DATE="2019-03-03",
                         DEEPGRB_RUN_LABEL="x", DEEPGRB_FORCE_TRAIN="1")
        self.assertEqual(p.returncode, 2)
        self.assertIn("requires DEEPGRB_TRAIN_SEED", p.stdout + p.stderr)

    @unittest.skipUnless((run_dir(*LEGACY_PERIOD) / "manifest.json").exists(), "2019 baseline run not on disk")
    def test_baseline_status_is_read_from_disk(self):
        p = run_pipeline("--dry-run")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Status of the run", p.stdout)
        self.assertIn("manifest coherent", p.stdout)


if __name__ == "__main__":
    unittest.main()
