"""
Compares the events of two runs (read-only): one-to-one pairing of [start, start + duration]
intervals extended by +/- 2 bins, then lists events present in only one run and paired events
whose time, duration, detectors, significance or tier changed.

Usage (repo root):
    python -m benchmark.audit.compare_runs <run A> <run B> [--out file.md]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.matching import overlap_one_to_one
from benchmark.validate import md_table

FIELDS = ["start_times", "duration", "detectors", "trig_dets", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE"]


def compare(run_a: Path, run_b: Path) -> dict:
    a = pd.read_csv(run_a / "results" / "events_table.csv")
    b = pd.read_csv(run_b / "results" / "events_table.csv")
    pairs = overlap_one_to_one(a["start_met"], a["duration"], b["start_met"], b["duration"])
    changed = []
    for i, j, _ in pairs:
        diffs = []
        for f in FIELDS:
            va, vb = a.at[i, f], b.at[j, f]
            same = (np.isclose(va, vb, rtol=0, atol=1e-9) if isinstance(va, (float, np.floating)) and isinstance(vb, (float, np.floating))
                    else str(va) == str(vb))
            if not same:
                diffs.append(f)
        if diffs:
            changed.append((i, j, diffs))
    paired_a = {i for i, _, _ in pairs}
    paired_b = {j for _, j, _ in pairs}
    return {"a": a, "b": b, "pairs": pairs, "changed": changed,
            "only_a": [i for i in range(len(a)) if i not in paired_a],
            "only_b": [j for j in range(len(b)) if j not in paired_b]}


def to_markdown(res: dict, name_a: str, name_b: str) -> str:
    a, b = res["a"], res["b"]
    cols = ["trig_ids", "start_times", "duration", "detectors", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE"]
    lines = [f"# Confronto eventi: `{name_a}` → `{name_b}`", "",
             f"- Eventi: {len(a)} → {len(b)}; coppie {len(res['pairs'])}; solo in {name_a}: {len(res['only_a'])}; "
             f"solo in {name_b}: {len(res['only_b'])}; coppie con differenze: {len(res['changed'])}.", ""]
    for i, j, diffs in res["changed"]:
        rows = pd.DataFrame([a.loc[i, cols].to_dict() | {"run": name_a}, b.loc[j, cols].to_dict() | {"run": name_b}])
        rows["start_times"] = rows["start_times"].astype(str).str.slice(0, 19)
        lines += [f"## Evento {a.at[i, 'trig_ids']} → {b.at[j, 'trig_ids']}: cambia {', '.join(diffs)}", "",
                  md_table(rows[["run"] + cols], ".3f"), ""]
    for label, idx, df in ((f"Solo in {name_a}", res["only_a"], a), (f"Solo in {name_b}", res["only_b"], b)):
        if idx:
            lines += [f"## {label}", "", md_table(df.loc[idx, cols], ".3f"), ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_a", type=Path)
    p.add_argument("run_b", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    text = to_markdown(compare(args.run_a, args.run_b), args.run_a.name, args.run_b.name)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
