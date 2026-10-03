import os
import sys
import numpy as np
import pandas as pd

class DualLogger:
    """Redirects stdout to both terminal and a specified text file."""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_csv = os.path.join(base_dir, "data", "results", "frg_03-2019_07-2019", "events_table_loc.csv")
    catalog_path = os.path.join(base_dir, "data", "DeepGRB_catalog.csv")
    report_txt = os.path.join(base_dir, "benchmark_summary_report.txt")
    
    # Enable dual logging (Console + TXT)
    logger = DualLogger(report_txt)
    sys.stdout = logger

    try:
        if not os.path.exists(target_csv):
            print(f"[ERROR] Pipeline output not found: {target_csv}")
            return
        if not os.path.exists(catalog_path):
            print(f"[ERROR] Reference catalog not found: {catalog_path}")
            return

        print(f"[INFO] Loading pipeline events: {target_csv}")
        df_mine = pd.read_csv(target_csv)
        print(f"[INFO] Loading Crupi catalog: {catalog_path}")
        df_cat = pd.read_csv(catalog_path)

        # Standardize datetime strings to YYYY-MM-DD HH:MM:SS
        df_mine["datetime_clean"] = pd.to_datetime(df_mine["start_times"].astype(str).str.slice(0, 19))
        df_cat["datetime_clean"] = pd.to_datetime(df_cat["datetime"].astype(str).str.slice(0, 19))

        print(f"[INFO] Total pipeline events : {len(df_mine)}")
        print(f"[INFO] Total catalog events  : {len(df_cat)}")

        # Filter catalog events belonging to 2019
        df_cat_2019 = df_cat[df_cat["datetime_clean"].dt.year == 2019].copy()
        print(f"[INFO] Crupi catalog events in 2019: {len(df_cat_2019)}")

        matched = []
        unmatched_mine = []
        tolerance_sec = 10.0

        for idx, row in df_mine.iterrows():
            t_mine = row["datetime_clean"]
            time_diffs = (df_cat_2019["datetime_clean"] - t_mine).abs().dt.total_seconds()
            min_diff = time_diffs.min()

            if pd.notna(min_diff) and min_diff <= tolerance_sec:
                best_idx = time_diffs.idxmin()
                cat_row = df_cat_2019.loc[best_idx]
                matched.append({
                    "pipeline_trig_id": row.get("trig_ids", idx),
                    "catalog_trig_id": cat_row.get("trig_ids", np.nan),
                    "pipeline_datetime": str(t_mine),
                    "catalog_datetime": str(cat_row["datetime_clean"]),
                    "delta_t_sec": min_diff,
                    "pipeline_label": str(row.get("catalog_triggers", "UNKNOWN")),
                    "crupi_label": str(cat_row.get("catalog_triggers", "UNKNOWN")),
                    "pipeline_ra": row.get("ra", np.nan),
                    "pipeline_dec": row.get("dec", np.nan),
                    "duration": row.get("duration", np.nan),
                    "sigma_r0": row.get("sigma_r0", np.nan),
                    "sigma_r1": row.get("sigma_r1", np.nan),
                    "sigma_r2": row.get("sigma_r2", np.nan)
                })
            else:
                unmatched_mine.append({
                    "pipeline_trig_id": row.get("trig_ids", idx),
                    "pipeline_datetime": str(t_mine),
                    "pipeline_label": str(row.get("catalog_triggers", "UNKNOWN")),
                    "ra": row.get("ra", np.nan),
                    "dec": row.get("dec", np.nan),
                    "duration": row.get("duration", np.nan)
                })

        df_matched = pd.DataFrame(matched)
        df_unmatched = pd.DataFrame(unmatched_mine)

        print("\n" + "=" * 60)
        print("        CRUPI BENCHMARK CROSS-MATCH REPORT (2019)")
        print("=" * 60)
        print(f"Total events analyzed in current run : {len(df_mine)}")
        print(f"Direct matches with Crupi 2019 paper : {len(df_matched)}")
        print(f"Potential sub-threshold / new events : {len(df_unmatched)}")

        if not df_matched.empty:
            exact_label = (df_matched["pipeline_label"] == df_matched["crupi_label"]).sum()
            print(f"\nExact Trigger Classification Matches : {exact_label} / {len(df_matched)} ({exact_label/len(df_matched)*100:.1f}%)")
            
            print("\nBreakdown of Matched Pipeline Labels:")
            print(df_matched["pipeline_label"].value_counts().head(10))

            print("\nBreakdown of Crupi Reference Labels:")
            print(df_matched["crupi_label"].value_counts().head(10))

        out_matched = os.path.join(os.path.dirname(target_csv), "benchmark_matched_crupi.csv")
        df_matched.to_csv(out_matched, index=False)
        print(f"\n[INFO] Matched comparison table saved to: {out_matched}")
        print(f"[INFO] Text report saved to: {report_txt}")
        print("=" * 60)

    finally:
        sys.stdout = logger.terminal
        logger.close()

if __name__ == "__main__":
    main()