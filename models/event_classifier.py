"""
Event classifier reproducing Crupi's deterministic heuristic rules.

The predicted class depends only on physical features (significance per range,
hardness ratios, Sun/Earth angular distances, SAA/pole proximity, galactic
latitude, duration, detector counts). Catalog columns are never read here; they
are used only by the validation (validation/validate.py).

Provenance: the rules are Crupi's "manual classification logic" in
upstream pipeline/script_classification2.py (2023). Their thresholds were read from
one-vs-rest decision trees (depth 3) and refined by hand on the labelled catalog of
2010-11, 2014 and 2019; random forests (with L1 feature selection and Anchor
explanations) were used there to study feature importance, not as the classifier.

Rules transcribed here: SF, TGF, GF, UNC(LP), GRB. Not available: the FP rule and the
light-curve features fe_* (wavelet entropy, skewness, ...) computed with tsfel in the
upstream branch ric_review_28062023. Without them the terms 'fe_wet > 2.054' (GRB) and
'fe_skw <= 0.345' (UNC(LP)) are neutral (defaults 2.1 and 0.0 make them always true).
Crupi evaluated each rule one-vs-rest; the single label below (priority GRB, TGF, SF,
UNC(LP), GF, UNC) is our convention.
"""

import logging
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


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
            "ra", "dec", "ra_std", "dec_std", "ra_earth", "dec_earth",
            "ra_sun", "dec_sun", "b_galactic", "lat_fermi", "lon_fermi", "l"
        ]
        for c in cols_direct:
            X[c] = df[c] if c in df.columns else 0.0
        X["earth_vis"] = df["earth_vis"].astype(float) if "earth_vis" in df.columns else 1.0

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
        # Crupi: (1 - earth_vis) | (diff_earth < 80)
        y_pred["TGF"] = (earth_vis_safe < 0.5) | (X["diff_earth"] < 80.0)
        y_pred["GF"] = (np.abs(X["b_galactic"]) < 10.0) & (earth_vis_safe > 0.5)
        y_pred["UNC(LP)"] = (
            (
                ((X["dist_saa_lon"] <= 9.0) & (X["dist_saa_lat"] <= 3.6)) |
                ((X["dist_polo_nord_lon"] <= 19.0) & (X["dist_polo_nord_lat"] <= 7.6)) |
                ((X["dist_polo_sud_lon"] <= 19.0) & (X["dist_polo_sud_lat"] <= 7.6))
            ) &
            ((X["num_det"] >= 9) | (X["fe_skw"] <= 0.345)) &
            # Crupi: (diff_sun > 35) | (max(ra_std, dec_std) > 100) with ra_std/dec_std holding the
            # localization *variance* (deg^2) in his tables; 100 deg^2 -> 10 deg standard deviation.
            ((X["diff_sun"] > 35.0) | (np.maximum(X["ra_std"], X["dec_std"]) > 10.0))
        )
        y_pred["GRB"] = (X["HR10"] > 0.449) & (X["HR21"] <= 0.375) & (X["fe_wet"] > 2.054)
        y_pred["UNC"] = 1 - (y_pred["SF"] | y_pred["TGF"] | y_pred["GF"] | y_pred["UNC(LP)"] | y_pred["GRB"])

        def resolve_label(row: pd.Series) -> str:
            # Physical features only: catalog columns must never decide the class (no leakage).
            for label in ["GRB", "TGF", "SF", "UNC(LP)", "GF", "UNC"]:
                if row[label]:
                    return label
            return "UNC"

        y_pred["predicted_class"] = y_pred.apply(resolve_label, axis=1)
        self.y_pred = y_pred
        return self.y_pred


CATALOG_COLUMNS = ["catalog_triggers"]  # kept in the output for reference, never used to classify
RULE_LABELS = ["GRB", "TGF", "SF", "UNC(LP)", "GF"]


def classify_events(loc_path: Path, out_path: Path) -> pd.DataFrame:
    """
    Classifies a localized event table with Crupi's rules (no catalog input) and writes
    events_classified.csv: one boolean column per rule (Crupi evaluated each rule one-vs-rest)
    and the single-label convention in predicted_class. Never overwrites.
    """
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError(f"Refusing to overwrite {out_path}")
    events = pd.read_csv(loc_path)
    features = events.drop(columns=[c for c in CATALOG_COLUMNS if c in events.columns])
    clf = CrupiEventClassifier(features)
    clf.prepare_features()
    y = clf.apply_classification_logic()
    for label in RULE_LABELS:
        events[f"rule_{label}"] = y[label].astype(bool).values
    events["predicted_class"] = y["predicted_class"].values
    events.to_csv(out_path, index=False)
    return events
