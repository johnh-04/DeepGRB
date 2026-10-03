"""
Sensitivity analysis (not a tuning): FOCuS t_max from the paper text (dmax = 120.4 s) instead of
the upstream code value (50 bins = 204.8 s), on the same background predictions.

Creates <run>-sens-tmax<N>/ with a link to the baseline pred/ folder, new trig/ and results/.
The baseline run is not modified. Validate it with:
    python -m benchmark.validate --run <that folder> --out benchmark/out/sensitivity_tmax<N>

Usage (from repo root): python -m benchmark.audit.sensitivity_tmax [--dmax 120.4]
"""

import argparse
import json
from pathlib import Path

from connections.utils.config import GBM_TRIG_DB, run_dir
from models.analyze import BINLENGTH, EventAnalyzer
from models.trigger import run_trigger
from models.trigs.focus import build_focus_runner

MU_MIN = 1.2
THRESHOLD = 3.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dmax", type=float, default=120.4, help="FOCuS maximum change-point age in seconds")
    args = parser.parse_args()
    t_max = int(args.dmax // BINLENGTH)

    base = run_dir()
    out = base.parent / f"{base.name}-sens-tmax{t_max}"
    (out / "results").mkdir(parents=True, exist_ok=True)
    if not (out / "pred").exists():
        (out / "pred").symlink_to(base / "pred", target_is_directory=True)
    manifest = json.loads((base / "manifest.json").read_text())
    manifest["parameters"]["focus"]["t_max_bins"] = t_max
    manifest["parameters"]["sensitivity_of"] = str(base.name)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    if not (out / "trig" / "trig.csv").exists():
        run_trigger(out / "pred" / "frg.csv", out / "pred" / "bkg.csv", out / "trig" / "trig.csv",
                    out / "trig" / "offset.csv", build_focus_runner(mu_min=MU_MIN, t_max=t_max))
    analyzer = EventAnalyzer(out / "pred" / "frg.csv", out / "pred" / "bkg.csv", out / "trig" / "trig.csv",
                             out / "trig" / "offset.csv", GBM_TRIG_DB)
    _, events = analyzer.run(THRESHOLD, out / "results")
    print(f"t_max = {t_max} bins ({t_max * BINLENGTH:.1f} s): {len(events)} events, CE {events['CE'].value_counts().to_dict()}")
    print(f"run folder: {out}")


if __name__ == "__main__":
    main()
