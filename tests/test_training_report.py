"""The training report is flushed line by line (readable under nohup / python -u)."""

import os
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


class TestReportFlush(unittest.TestCase):
    def test_report_is_flushed_before_exit(self):
        code = "from models.model_nn import report; report('READY'); import time; time.sleep(20)"
        proc = subprocess.Popen([PY, "-u", "-c", code], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            deadline, line = time.time() + 120, ""
            while time.time() < deadline and "READY" not in line:
                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if ready:
                    line = proc.stdout.readline()
            self.assertIn("READY", line)
            self.assertIsNone(proc.poll())  # still running: the line arrived before exit
        finally:
            proc.kill()


if __name__ == "__main__":
    unittest.main()
