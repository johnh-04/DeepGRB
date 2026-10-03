"""
LaTeX table formatter module.
Aggregates detected candidate events from the three historical epochs
and formats them for scientific publication / LaTeX thesis tables.
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd

from connections.utils.config import DATA_DIR, FOLD_RES, DEEP_GRB_CSV
from pipeline.manual_label import (
    P_MANUAL_2011, P_MANUAL_2014, P_MANUAL_2019,
    EVENT_2010, EVENT_2014, EVENT_2019, THE_EVENTS, SELECTED_TRIG_EVE
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def generate_latex_tables(save_to_file: bool = True) -> None:
    """Consolidates event tables from all epochs and generates LaTeX tables."""
    periods = [
        ("frg_11-2010_02-2011", P_MANUAL_2011),
        ("frg_01-2014_03-2014", P_MANUAL_2014),
        ("frg_03-2019_07-2019", P_MANUAL_2019),
    ]

    dfs = []
    for folder_name, labels in periods:
        p_path = DATA_DIR / FOLD_RES / folder_name / "events_table.csv"
        if not p_path.exists():
            logging.warning(f"Events table missing at: {p_path}")
            continue
        sub_df = pd.read_csv(p_path)
        sub_df["catalog_triggers"] = list(labels[:len(sub_df)])
        dfs.append(sub_df)

    if not dfs:
        raise FileNotFoundError("No candidate events tables found across historical periods.")

    df_all = pd.concat(dfs, ignore_index=True)
    df_all.drop(columns=[c for c in ["start_index", "end_index", "end_times"] if c in df_all.columns], inplace=True)

    df_all["period"] = df_all["start_times"].astype(str).str.slice(0, 4).apply(lambda x: "2010" if x == "2011" else x)
    df_all["trig_ids"] = df_all["period"] + "_" + df_all["trig_ids"].astype(str)
    df_all["datetime"] = df_all["start_times"].astype(str).str.slice(0, 19)

    if "trig_dets" in df_all.columns:
        df_all["det trigs"] = df_all["trig_dets"].apply(
            lambda x: " ".join(sorted(list({d.split("_")[0] for d in str(x).split()})))
        )
    else:
        df_all["det trigs"] = ""

    for c in ["start_met", "end_met"]:
        if c in df_all.columns:
            df_all[c] = df_all[c].astype(int)

    for c in ["sigma_r0", "sigma_r1", "sigma_r2", "duration"]:
        if c in df_all.columns:
            df_all[c] = df_all[c].round(2)

    df_all["sigma_max"] = df_all[["sigma_r0", "sigma_r1", "sigma_r2"]].max(axis=1)

    # Filter false alarms and annotate UNKNOWN
    cols_summary = ["trig_ids", "datetime", "duration", "det trigs", "catalog_triggers", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_max"]
    df_filtered = df_all[[c for c in cols_summary if c in df_all.columns]].copy()
    df_filtered = df_filtered[~df_filtered["catalog_triggers"].isin(["f", "f (ssa)"])].reset_index(drop=True)
    df_filtered["catalog_triggers"] = df_filtered["catalog_triggers"].replace("u", "UNKNOWN")

    # Merge tentative class labels
    classes_list = [
        pd.DataFrame({"trig_ids": [f"2010_{k}" for k in EVENT_2010], "class": list(EVENT_2010.values())}),
        pd.DataFrame({"trig_ids": [f"2014_{k}" for k in EVENT_2014], "class": list(EVENT_2014.values())}),
        pd.DataFrame({"trig_ids": [f"2019_{k}" for k in EVENT_2019], "class": list(EVENT_2019.values())}),
    ]
    df_classes = pd.concat(classes_list, ignore_index=True)
    df_merged = pd.merge(df_filtered, df_classes, how="left", on=["trig_ids"])
    df_merged["class"] = df_merged["class"].fillna("")

    is_unk = df_merged["catalog_triggers"] == "UNKNOWN"
    df_merged.loc[is_unk, "catalog_triggers"] = "UNKNOWN: " + df_merged.loc[is_unk, "class"]
    df_merged.drop(columns=["class"], inplace=True)

    # Highlight benchmark events
    for t_id in THE_EVENTS:
        df_merged.loc[df_merged["trig_ids"] == t_id, "trig_ids"] = t_id + "*"

    # Output LaTeX tables
    latex_unk = df_merged[is_unk].to_latex(index=False)
    latex_known = df_merged[~is_unk].to_latex(index=False)

    if save_to_file:
        out_tex_path = DATA_DIR / "plots" / "tables_publication.tex"
        with open(out_tex_path, "w") as f:
            f.write("% UNKNOWN CANDIDATE EVENTS\n")
            f.write(latex_unk)
            f.write("\n\n% CONFIRMED CATALOG TRIGGERS\n")
            f.write(latex_known)
        logging.info(f"LaTeX tables written successfully to: {out_tex_path}")

    print("\n[PREVIEW LATEX UNKNOWN EVENTS TABLE]:\n")
    print(latex_unk[:800] + "\n... [TRUNCATED] ...\n")


if __name__ == "__main__":
    generate_latex_tables()