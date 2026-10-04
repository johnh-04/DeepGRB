"""Tests for labelled runs and forced retraining (utils/run_options.py, ModelNN.train report)."""

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_model_nn import ModelTestCase
from utils.run_options import LEGACY_H5_NAME, RunOptionsError, obtain_model, resolve_run_options

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
P2019 = ("2019-03-01", "2019-06-30")
TOY_PARAMS = {"units": 8, "epochs": 2, "bs": 16}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OptionsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.nn_dir = root / "nn_model"
        self.runs = root / "runs" / "2019-03-01_2019-06-30"
        self.default_run = self.runs / "engine-v2"
        self.default_run.mkdir(parents=True)
        # legacy model and its bundle, deliberately corrupt: loading them would raise
        self.legacy_h5 = self.nn_dir / LEGACY_H5_NAME
        self.legacy_bundle = self.nn_dir / "bundles" / Path(LEGACY_H5_NAME).stem
        self.legacy_bundle.mkdir(parents=True)
        self.legacy_h5.write_bytes(b"not a model")
        (self.legacy_bundle / "model.h5").write_bytes(b"not a model")
        (self.legacy_bundle / "metadata.json").write_text(json.dumps({"model_file": "model.h5", "source": "legacy_h5"}))
        (self.legacy_bundle / "scaler.joblib").write_bytes(b"not a scaler")

    def tearDown(self):
        self._tmp.cleanup()

    def resolve(self, **env):
        return resolve_run_options(env, *P2019, self.default_run, self.nn_dir)


class TestResolve(OptionsTestCase):
    def test_default_behaviour_unchanged(self):
        o = self.resolve()
        self.assertEqual((o.run_dir, o.bundle_dir, o.mode, o.seed, o.label), (self.default_run, self.legacy_bundle, "load_bundle", 0, None))

    def test_default_wraps_legacy_when_no_bundle(self):
        for f in self.legacy_bundle.iterdir():
            f.unlink()
        self.legacy_bundle.rmdir()
        self.assertEqual(self.resolve().mode, "wrap_legacy")

    def test_force_train_never_targets_legacy(self):
        o = self.resolve(DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="1", DEEPGRB_FORCE_TRAIN="1")
        self.assertEqual(o.mode, "train")
        self.assertEqual(o.seed, 1)
        self.assertEqual(o.run_dir, self.runs / "engine-v2-seed1")
        self.assertEqual(o.bundle_dir, self.nn_dir / "bundles" / "model_2019-03-01_2019-06-30_seed1")
        self.assertNotEqual(o.bundle_dir, self.legacy_bundle)

    def test_force_requires_label_and_seed(self):
        with self.assertRaises(RunOptionsError):
            self.resolve(DEEPGRB_FORCE_TRAIN="1", DEEPGRB_TRAIN_SEED="1")
        with self.assertRaises(RunOptionsError):
            self.resolve(DEEPGRB_FORCE_TRAIN="1", DEEPGRB_RUN_LABEL="seed1")
        with self.assertRaises(RunOptionsError):
            self.resolve(DEEPGRB_FORCE_TRAIN="1", DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="one")

    def test_invalid_label(self):
        with self.assertRaises(RunOptionsError):
            self.resolve(DEEPGRB_RUN_LABEL="../x")

    def test_existing_labelled_run_folder_stops(self):
        (self.runs / "engine-v2-seed1").mkdir()
        with self.assertRaises(RunOptionsError):
            self.resolve(DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="1", DEEPGRB_FORCE_TRAIN="1")

    def test_existing_labelled_bundle_needs_reuse_flag(self):
        (self.nn_dir / "bundles" / "model_2019-03-01_2019-06-30_seed1").mkdir()
        env = dict(DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="1", DEEPGRB_FORCE_TRAIN="1")
        with self.assertRaises(RunOptionsError):
            self.resolve(**env)
        self.assertEqual(self.resolve(DEEPGRB_REUSE_BUNDLE="1", **env).mode, "load_bundle")

    def test_unlabelled_missing_model_fails_only_when_needed(self):
        o = resolve_run_options({}, "2024-01-01", "2024-01-31", self.runs / "x", self.nn_dir)
        self.assertEqual(o.mode, "unavailable")
        with self.assertRaises(RunOptionsError):
            obtain_model(object(), o, {})


class TestReuseAcrossEngineVersions(OptionsTestCase):
    """engine-v3 runs reuse pred/ and trig/ of the matching engine-v2 run (step 5 only changes)."""

    def make_source(self, name: str, bundle: str):
        src = self.runs / name
        for f in ("pred/frg.csv", "pred/bkg.csv", "trig/trig.csv", "trig/offset.csv"):
            (src / f).parent.mkdir(parents=True, exist_ok=True)
            (src / f).write_text("x")
        (src / "manifest.json").write_text(json.dumps({"parameters": {"model_bundle": bundle}}))
        return src

    def resolve_v3(self, **env):
        return resolve_run_options(env, *P2019, self.runs / "engine-v3", self.nn_dir, reuse_source_dir=self.default_run)

    def test_unlabelled_v3_reuses_v2(self):
        self.make_source("engine-v2", "data/nn_model/bundles/legacy")
        o = self.resolve_v3()
        self.assertEqual((o.mode, o.run_dir, o.reuse_source), ("reuse_pred", self.runs / "engine-v3", self.default_run))
        self.assertEqual(str(o.bundle_dir), "data/nn_model/bundles/legacy")

    def test_labelled_v3_reuses_labelled_v2_without_bundle_checks(self):
        self.make_source("engine-v2-seed1", "data/nn_model/bundles/model_seed1")
        (self.nn_dir / "bundles" / "model_2019-03-01_2019-06-30_seed1").mkdir()  # would need REUSE_BUNDLE otherwise
        o = self.resolve_v3(DEEPGRB_RUN_LABEL="seed1")
        self.assertEqual((o.mode, o.run_dir), ("reuse_pred", self.runs / "engine-v3-seed1"))
        self.assertEqual(o.reuse_source, self.runs / "engine-v2-seed1")

    def test_force_train_never_reuses(self):
        self.make_source("engine-v2-seed1", "x")
        o = self.resolve_v3(DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="1", DEEPGRB_FORCE_TRAIN="1")
        self.assertEqual(o.mode, "train")

    def test_incomplete_source_is_not_reused(self):
        src = self.make_source("engine-v2-seed2", "x")
        (src / "trig" / "offset.csv").unlink()
        with self.assertRaises(RunOptionsError):  # falls back to the normal rules: no bundle, no training flag
            self.resolve_v3(DEEPGRB_RUN_LABEL="seed2")

    def test_existing_labelled_v3_folder_stops(self):
        self.make_source("engine-v2-seed1", "x")
        (self.runs / "engine-v3-seed1").mkdir()
        with self.assertRaises(RunOptionsError):
            self.resolve_v3(DEEPGRB_RUN_LABEL="seed1")


class FakeNN:
    def __init__(self):
        self.calls = []

    def load_bundle(self, *a):
        self.calls.append("load_bundle")

    def bundle_from_legacy_h5(self, *a):
        self.calls.append("bundle_from_legacy_h5")

    def train(self, bundle_dir, seed, extra_metadata, **params):
        self.calls.append(("train", Path(bundle_dir).name, seed))


class TestObtainModel(OptionsTestCase):
    def test_force_calls_only_train(self):
        nn = FakeNN()
        obtain_model(nn, self.resolve(DEEPGRB_RUN_LABEL="seed1", DEEPGRB_TRAIN_SEED="7", DEEPGRB_FORCE_TRAIN="1"), {})
        self.assertEqual(nn.calls, [("train", "model_2019-03-01_2019-06-30_seed1", 7)])


class TestForcedTrainingWithRealModel(ModelTestCase):
    """Real ModelNN on toy data: the corrupt legacy model must not be touched."""

    def test_legacy_not_loaded_and_report_written(self):
        nn_dir = self.root / "nn_model"
        legacy_bundle = nn_dir / "bundles" / Path(LEGACY_H5_NAME).stem
        legacy_bundle.mkdir(parents=True)
        (nn_dir / LEGACY_H5_NAME).write_bytes(b"not a model")
        (legacy_bundle / "model.h5").write_bytes(b"not a model")
        (legacy_bundle / "metadata.json").write_text(json.dumps({"model_file": "model.h5"}))
        before = {p: sha(p) for p in [nn_dir / LEGACY_H5_NAME, *legacy_bundle.iterdir()]}

        opts = resolve_run_options({"DEEPGRB_RUN_LABEL": "seed3", "DEEPGRB_TRAIN_SEED": "3", "DEEPGRB_FORCE_TRAIN": "1"},
                                   *P2019, self.root / "runs" / "engine-v2", nn_dir)
        nn = self.model()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            obtain_model(nn, opts, TOY_PARAMS, extra_metadata={"git_commit": "abc123", "run_label": "seed3"})
        log = out.getvalue()

        self.assertEqual({p: sha(p) for p in before}, before)  # legacy files untouched
        meta = json.loads((opts.bundle_dir / "metadata.json").read_text())
        self.assertEqual(meta["seed"], 3)
        self.assertEqual(meta["git_commit"], "abc123")
        self.assertEqual(meta["period"], {"start_date": "2019-03-01", "end_date": "2019-03-02"})
        self.assertIn("training_seconds", meta)
        self.assertIn("tensorflow", meta["versions"])
        self.assertEqual(len(meta["metrics"]), 36)
        for needle in ("[train] seed        : 3", "[train] rows", "[train] epoch   1/2", "[train] epoch   2/2",
                       "per-channel MAE", "n0_r0", "[train] fit time"):
            self.assertIn(needle, log)
        with self.assertRaises(FileExistsError):  # a bundle is never overwritten
            nn.train(opts.bundle_dir, seed=3, **TOY_PARAMS)


if __name__ == "__main__":
    unittest.main()
