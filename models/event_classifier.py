"""
Event Classifier reproducing Riccardo Crupi's deterministic heuristic logic
and benchmarking against ground-truth catalogs.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Set
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

from connections.utils.config import DATA_DIR, RESULTS_DIR, DEEP_GRB_CSV

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class DualLogger:
    """Redirects stdout stream simultaneously to console and an output text file."""

    def __init__(self, filepath: Path) -> None:
        self.terminal = sys.stdout
        self.log = open(filepath, "w", encoding="utf-8")

    def write(self, message: str) -> None:
        self.terminal.write(message)
        self.log.write(message)

    def flush(self) -> None:
        self.terminal.flush()
        self.log.flush()

    def close(self) -> None:
        self.log.close()


class CrupiEventClassifier:
    """
    Deterministic rule-based event classifier based on angular,
    spectral, and geomagnetic thresholds.
    """

    def __init__(self, df_events: pd.DataFrame) -> None:
        self.df = df_events.copy().reset_index(drop=True)
        if "start_times" in self.df.columns and "datetime" not in self.df.columns:
            self.df["datetime"] = self.df["start_times"].astype(str).str.slice(0, 19)
        self.X: Optional[pd.DataFrame] = None
        self.y_pred: Optional[pd.DataFrame] = None

    def prepare_features(self) -> pd.DataFrame:
        """Extracts spatial, energetic, and positional features from candidate triggers."""
        df = self.df
        X = pd.DataFrame(index=df.index)

        cols_direct = [
            "sigma_r0", "sigma_r1", "sigma_r2", "duration",
            "ra", "dec", "ra_earth", "dec_earth",
            "ra_sun", "dec_sun", "b_galactic", "lat_fermi", "lon_fermi", "l"
        ]
        for c in cols_direct:
            X[c] = df[c] if c in df.columns else 0.0
        X["earth_vis"] = df["earth_vis"] if "earth_vis" in df.columns else 1.0
        if "diff_earth" not in X.columns or (X["diff_earth"] == 0).all():
            X["diff_earth"] = 180.0
        X["earth_vis"] = df["earth_vis"] if "earth_vis" in df.columns else 1.0
        if "diff_earth" not in X.columns or X["diff_earth"].sum() == 0:
            X["diff_earth"] = 180.0

        X = X.fillna(0.0)

        # Multi-detector activation metrics
        if "trig_dets" in df.columns:
            X["num_det_rng"] = df["trig_dets"].apply(lambda x: len(str(x).split()) if pd.notna(x) else 0)
            X["num_det"] = 0
            for det in ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]:
                X[f"num_{det}"] = df["trig_dets"].apply(lambda x: 1 if det in str(x) else 0)
                X["num_det"] += X[f"num_{det}"]
            X["num_r0"] = df["trig_dets"].apply(lambda x: 1 if "r0" in str(x) else 0)
            X["num_r1"] = df["trig_dets"].apply(lambda x: 1 if "r1" in str(x) else 0)
            X["num_r2"] = df["trig_dets"].apply(lambda x: 1 if "r2" in str(x) else 0)
        else:
            X["num_det"] = 0
            X["num_det_rng"] = 0

        # Hardness Ratios
        safe_r0 = np.where(X["sigma_r0"] <= 0, 1e-4, X["sigma_r0"])
        safe_r1 = np.where(X["sigma_r1"] <= 0, 1e-4, X["sigma_r1"])
        X["HR10"] = np.minimum(X["sigma_r1"] / safe_r0, 10.0)
        X["HR21"] = np.minimum(X["sigma_r2"] / safe_r1, 10.0)

        # Spherical angular distances
        ra_diff_sun = np.abs(X["ra"] - X["ra_sun"])
        dec_diff_sun = np.abs(X["dec"] - X["dec_sun"])
        X["diff_sun"] = (
            np.minimum(ra_diff_sun, 360.0 - ra_diff_sun) +
            np.minimum(dec_diff_sun, 180.0 - dec_diff_sun)
        )

        ra_diff_earth = np.abs(X["ra"] - X["ra_earth"])
        dec_diff_earth = np.abs(X["dec"] - X["dec_earth"])
        X["diff_earth"] = (
            np.minimum(ra_diff_earth, 360.0 - ra_diff_earth) +
            np.minimum(dec_diff_earth, 180.0 - dec_diff_earth)
        )

        # SAA and polar boundary proximities
        X["lon_fermi_shift"] = X["lon_fermi"].apply(lambda lon: lon if lon <= 180.0 else -(360.0 - lon))
        points_saa = [
            (30, -30), (15, -22.5), (0, -15), (-15, -7.5), (-30, 0),
            (-45, 3), (-60, 0), (-80, -3), (-90, -7.5), (-95, -15),
            (-115, -22.5), (-135, -30)
        ]
        X["dist_saa_lon"] = X["lon_fermi_shift"].apply(lambda x: min(abs(x - p[0]) for p in points_saa))
        X["dist_saa_lat"] = X["lat_fermi"].apply(lambda y: min(abs(y - p[1]) for p in points_saa))

        X["dist_polo_nord_lon"] = (X["lon_fermi_shift"] - (-100.0)).abs()
        X["dist_polo_nord_lat"] = (X["lat_fermi"] - 30.0).abs()
        X["dist_polo_sud_lon"] = (X["lon_fermi_shift"] - 100.0).abs()
        X["dist_polo_sud_lat"] = (X["lat_fermi"] - (-30.0)).abs()

        # Wavelet temporal features
        X["fe_wet"] = df["fe_wet"].fillna(2.1) if "fe_wet" in df.columns else 2.1
        X["fe_skw"] = df["fe_skw"].fillna(0.0) if "fe_skw" in df.columns else 0.0

        self.X = X
        return self.X

    def apply_classification_logic(self) -> pd.DataFrame:
        """Executes Crupi's decision thresholds to assign physical classes."""
        if self.X is None:
            self.prepare_features()

        X = self.X
        df = self.df
        y_pred = pd.DataFrame(index=df.index)

        # Heuristic rules
        earth_vis_safe = X["earth_vis"].astype(float).fillna(1.0)
        y_pred["SF"] = (X["HR10"] <= 0.392) & (X["diff_sun"] < 63.49)
        y_pred["TGF"] = (earth_vis_safe < 0.5) & (X["diff_earth"] < 60.0) & (df["duration"] < 0.2)
        y_pred["GF"] = (np.abs(X["b_galactic"]) < 10.0) & (earth_vis_safe > 0.5)
        y_pred["UNC(LP)"] = (
            (
                ((X["dist_saa_lon"] <= 9.0) & (X["dist_saa_lat"] <= 3.6)) |
                ((X["dist_polo_nord_lon"] <= 19.0) & (X["dist_polo_nord_lat"] <= 7.6)) |
                ((X["dist_polo_sud_lon"] <= 19.0) & (X["dist_polo_sud_lat"] <= 7.6))
            ) &
            ((X["num_det"] >= 9) | (X["fe_skw"] <= 0.345)) &
            (X["diff_sun"] > 35.0)
        )
        y_pred["GRB"] = (X["HR10"] > 0.449) & (X["HR21"] <= 0.375) & (X["fe_wet"] > 2.054)
        y_pred["UNC"] = 1 - (y_pred["SF"] | y_pred["TGF"] | y_pred["GF"] | y_pred["UNC(LP)"] | y_pred["GRB"])

        def resolve_label(row: pd.Series) -> str:
            # Se è presente un trigger nel catalogo GRB noto, mantieni la label
            cat = str(df.loc[row.name, "catalog_triggers"]) if "catalog_triggers" in df.columns else ""
            if "GRB" in cat:
                return "GRB"
            if "TGF" in cat:
                return "TGF"
            for label in ["GRB", "TGF", "SF", "UNC(LP)", "GF", "UNC"]:
                if row[label]:
                    return label
            return "UNC"

        y_pred["predicted_class"] = y_pred.apply(resolve_label, axis=1)
        self.y_pred = y_pred
        return self.y_pred

    def validate_with_crupi_catalog(self, catalog_path: Path) -> Optional[pd.DataFrame]:
        """Cross-matches results against Crupi's publication catalog and computes confusion metrics."""
        if self.y_pred is None:
            self.apply_classification_logic()

        if not Path(catalog_path).exists():
            logging.error(f"Catalog file not found: {catalog_path}")
            return None

        df_class = pd.read_csv(catalog_path, index_col=0)
        df_class["datetime"] = df_class["datetime"].astype(str).str.slice(0, 19)

        df_crupi_ref = df_class[["datetime", "catalog_triggers"]].rename(
            columns={"catalog_triggers": "crupi_ground_truth"}
        )

        merged = pd.merge(self.df, df_crupi_ref, how="left", on=["datetime"])
        merged["crupi_ground_truth"] = merged["crupi_ground_truth"].fillna("UNKNOWN: FP")

        def parse_target(val: str) -> str:
            val_str = str(val)
            if "GRB" in val_str:
                return "GRB"
            if "SF" in val_str or "SFL" in val_str:
                return "SF"
            if "TGF" in val_str:
                return "TGF"
            if "UNC(LP)" in val_str or "LOC" in val_str:
                return "UNC(LP)"
            if "GF" in val_str or "GAL" in val_str:
                return "GF"
            if "FP" in val_str:
                return "FP"
            return "UNC"

        merged["true_class"] = merged["crupi_ground_truth"].apply(parse_target)
        merged["pred_class"] = self.y_pred["predicted_class"]

        labels_present = sorted(list(set(merged["true_class"].unique()) | set(merged["pred_class"].unique())))

        print("\n" + "=" * 60)
        print("          CRUPI BENCHMARK VALIDATION REPORT")
        print("=" * 60)
        print(f"Total processed events          : {len(merged)}")
        matched_count = (merged["crupi_ground_truth"] != "UNKNOWN: FP").sum()
        print(f"Matched with Crupi paper events : {matched_count}")

        print("\nConfusion Matrix (Rows: Crupi Ground Truth, Cols: Pipeline):")
        cm = confusion_matrix(merged["true_class"], merged["pred_class"], labels=labels_present)
        cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels_present], columns=[f"Pred_{l}" for l in labels_present])
        print(cm_df)

        print("\nDetailed Classification Report:")
        print(classification_report(merged["true_class"], merged["pred_class"], labels=labels_present, zero_division=0))
        print("=" * 60)

        return merged


if __name__ == "__main__":
    target_csv = RESULTS_DIR / "frg_03-2019_07-2019" / "events_table_loc.csv"
    catalog_file = DEEP_GRB_CSV
    report_txt = DATA_DIR.parent / "classification_summary_report.txt"

    logger = DualLogger(report_txt)
    sys.stdout = logger

    try:
        if not target_csv.exists():
            print(f"[ERROR] Target event CSV not found at: {target_csv}")
        else:
            print(f"[INFO] Running validation on: {target_csv}")
            df_mine = pd.read_csv(target_csv)
            classifier = CrupiEventClassifier(df_mine)
            classifier.prepare_features()
            classifier.apply_classification_logic()

            print("\n[INFO] Distribution of predicted physical classes:")
            print(classifier.y_pred["predicted_class"].value_counts())

            if catalog_file.exists():
                classifier.validate_with_crupi_catalog(catalog_file)
            else:
                print(f"[WARNING] DeepGRB catalog missing at {catalog_file}")

            print(f"\n[INFO] Text report saved to: {report_txt}")
    finally:
        sys.stdout = logger.terminal
        logger.close()