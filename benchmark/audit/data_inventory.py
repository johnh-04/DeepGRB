"""
Read-only data coverage inventory for the Crupi 2019 window.

For every calendar day in [START, END] (inclusive) reports which raw and
preprocessed inputs exist on disk:
  - CSPEC files: NaI (n0..nb, expected 12) and BGO (b0, b1, expected 2)
  - POSHIST file (expected 1)
  - preprocessed daily table data/bkg/YYMMDD.csv
and whether the day is covered by the prediction matrices (pred/frg_*.csv).

Writes docs/DATA_INVENTORY.md and docs/data_inventory.csv. Never modifies data.

Usage (from repo root):
    python -m benchmark.audit.data_inventory [--start YYYY-MM-DD] [--end YYYY-MM-DD]

Defaults: START_DATE / END_DATE from connections/utils/config.py.
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from connections.utils.config import END_DATE, START_DATE

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"

NAI_DETS = [f"n{d}" for d in "0123456789ab"]
BGO_DETS = ["b0", "b1"]
CSPEC_RE = re.compile(r"glg_cspec_(n[0-9ab]|b[01])_(\d{6})_v(\d{2})\.pha$")
POSHIST_RE = re.compile(r"glg_poshist_all_(\d{6})_v(\d{2})\.fit$")


def scan_cspec(folder: Path) -> dict:
    """Maps YYMMDD -> {detector: [versions]}."""
    out = defaultdict(lambda: defaultdict(list))
    if folder.exists():
        for f in folder.iterdir():
            m = CSPEC_RE.match(f.name)
            if m:
                out[m.group(2)][m.group(1)].append(m.group(3))
    return out


def scan_poshist(folder: Path) -> dict:
    """Maps YYMMDD -> [versions]."""
    out = defaultdict(list)
    if folder.exists():
        for f in folder.iterdir():
            m = POSHIST_RE.match(f.name)
            if m:
                out[m.group(1)].append(m.group(2))
    return out


def pred_day_coverage(pred_file: Path) -> set:
    """Returns the set of YYMMDD days that have at least one row in a pred matrix."""
    if not pred_file.exists():
        return set()
    ts = pd.read_csv(pred_file, usecols=["timestamp"])["timestamp"].dropna()
    return set(pd.to_datetime(ts.str.slice(0, 10)).dt.strftime("%y%m%d").unique())


def build_inventory(start: str, end: str) -> pd.DataFrame:
    cspec = scan_cspec(DATA_DIR / "cspec")
    poshist = scan_poshist(DATA_DIR / "poshist")
    bkg_dir = DATA_DIR / "bkg"
    pred_days = pred_day_coverage(DATA_DIR / "pred" / "frg_03-2019_07-2019.csv")

    rows = []
    for day in pd.date_range(start, end, freq="D"):
        d = day.strftime("%y%m%d")
        dets = cspec.get(d, {})
        n_nai = sum(1 for k in NAI_DETS if k in dets)
        n_bgo = sum(1 for k in BGO_DETS if k in dets)
        versions = sorted({v for vs in dets.values() for v in vs})
        n_pos = len(poshist.get(d, []))
        rows.append({
            "date": day.strftime("%Y-%m-%d"),
            "yymmdd": d,
            "cspec_nai": n_nai,
            "cspec_bgo": n_bgo,
            "cspec_versions": ",".join(f"v{v}" for v in versions),
            "poshist": n_pos,
            "bkg_csv": (bkg_dir / f"{d}.csv").exists(),
            "in_pred_frg": d in pred_days,
            "raw_complete": n_nai == 12 and n_bgo == 2 and n_pos >= 1,
        })
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame, start: str, end: str) -> str:
    n = len(df)
    lines = [
        "# Inventario copertura dati",
        "",
        f"Finestra: {start} → {end} (inclusiva), {n} giorni. "
        "Generato da `python -m benchmark.audit.data_inventory` (sola lettura).",
        "",
        "## Riepilogo",
        "",
        "| Voce | Giorni |",
        "|---|---|",
        f"| Dati grezzi completi (12 NaI + 2 BGO CSPEC + POSHIST) | {int(df.raw_complete.sum())} / {n} |",
        f"| CSPEC NaI completi (12/12) | {int((df.cspec_nai == 12).sum())} / {n} |",
        f"| POSHIST presente | {int((df.poshist >= 1).sum())} / {n} |",
        f"| Tabella preprocessata `data/bkg/YYMMDD.csv` | {int(df.bkg_csv.sum())} / {n} |",
        f"| Presente in `pred/frg_03-2019_07-2019.csv` | {int(df.in_pred_frg.sum())} / {n} |",
        "",
    ]
    missing_raw = df.loc[~df.raw_complete, "date"].tolist()
    missing_bkg = df.loc[df.raw_complete & ~df.bkg_csv, "date"].tolist()
    missing_pred = df.loc[df.bkg_csv & ~df.in_pred_frg, "date"].tolist()
    lines += [
        "## Buchi",
        "",
        f"- Giorni senza dati grezzi completi ({len(missing_raw)}): {', '.join(missing_raw) or 'nessuno'}",
        f"- Grezzi completi ma senza `bkg` ({len(missing_bkg)}): {', '.join(missing_bkg) or 'nessuno'}",
        f"- Con `bkg` ma assenti da `pred/frg` ({len(missing_pred)}): {', '.join(missing_pred) or 'nessuno'}",
        "",
        "## Dettaglio giorno per giorno",
        "",
        "| Data | CSPEC NaI | CSPEC BGO | Versioni | POSHIST | bkg csv | in pred | Completo |",
        "|---|---|---|---|---|---|---|---|",
    ]
    yn = lambda b: "sì" if b else "**no**"
    for r in df.itertuples():
        lines.append(
            f"| {r.date} | {r.cspec_nai}/12 | {r.cspec_bgo}/2 | {r.cspec_versions or '-'} | "
            f"{r.poshist} | {yn(r.bkg_csv)} | {yn(r.in_pred_frg)} | {yn(r.raw_complete)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    args = parser.parse_args()

    df = build_inventory(args.start, args.end)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DOCS_DIR / "data_inventory.csv", index=False)
    (DOCS_DIR / "DATA_INVENTORY.md").write_text(to_markdown(df, args.start, args.end), encoding="utf-8")
    print(f"days={len(df)} raw_complete={int(df.raw_complete.sum())} "
          f"bkg_csv={int(df.bkg_csv.sum())} in_pred={int(df.in_pred_frg.sum())}")
    print("missing raw:", df.loc[~df.raw_complete, "date"].tolist())


if __name__ == "__main__":
    main()
