"""Importing the pipeline must not log into the HEASARC FTP server (gbm.finder does it at import)."""

import os
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


class TestNoFtpOnImport(unittest.TestCase):
    def test_pipeline_import_does_not_contact_ftp(self):
        code = ("import runpy, sys; runpy.run_path('pipeline/pipeline_bkg.py', run_name='not_main'); "
                "print('FINDER_LOADED' if 'gbm.finder' in sys.modules else 'FINDER_NOT_LOADED')")
        env = {k: v for k, v in os.environ.items() if not k.startswith("DEEPGRB_")}
        out = subprocess.run([PY, "-c", code], cwd=REPO, capture_output=True, text=True, env=env, timeout=600)
        self.assertIn("FINDER_NOT_LOADED", out.stdout, out.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
