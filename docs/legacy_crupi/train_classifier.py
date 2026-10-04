"""
Supervised Machine Learning benchmark and feature selection pipeline.
Compares Random Forest, Decision Tree, and L1-penalized LinearSVC against paper labels.
"""

import logging
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn import tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import QuantileTransformer
from sklearn.svm import LinearSVC
from sklearn.feature_selection import SelectFromModel

from connections.utils.config import DATA_DIR, FOLD_RES, DEEP_GRB_CSV

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Load reference catalog from Crupi et al.
if not Path(DEEP_GRB_CSV).exists():
    raise FileNotFoundError(f"DeepGRB reference catalog missing: {DEEP_GRB_CSV}")

df_class = pd.read_csv(DEEP_GRB_CSV, index_col=0)

# Concatenate all three analyzed historical epochs
catalog_dfs = []
for start_m, end_m in [("03-2019", "07-2019"), ("01-2014", "03-2014"), ("11-2010", "02-2011")]:
    ev_path = DATA_DIR / FOLD_RES / f"frg_{start_m}_{end_m}" / "events_table_loc_wavelet_norm_ext_bkg2.csv"
    if not ev_path.exists():
        # Fallback to standard loc table if wavelet-normalized table is not generated
        ev_path = DATA_DIR / FOLD_RES / f"frg_{start_m}_{end_m}" / "events_table_loc.csv"

    if ev_path.exists():
        catalog_dfs.append(pd.read_csv(ev_path))
    else:
        logging.warning(f"Epoch table not found: {ev_path}")

if not catalog_dfs:
    raise FileNotFoundError("No event tables found across historical periods to benchmark.")

df_catalog = pd.concat(catalog_dfs, ignore_index=True)
df_catalog["datetime"] = df_catalog["start_times"].astype(str).str.slice(0, 19)

# Align with reference labels
df_catalog = pd.merge(df_catalog, df_class[["datetime", "catalog_triggers"]], how="left", on=["datetime"])
df_catalog["catalog_triggers"] = df_catalog["catalog_triggers_y"].fillna("UNKNOWN: FP")
df_catalog.drop(columns=[c for c in ["catalog_triggers_x", "catalog_triggers_y"] if c in df_catalog.columns], inplace=True)

idx_unknown = df_catalog["catalog_triggers"].str.contains("UNKNOWN")
ev_type_list = ["GRB", "SF", "UNC(LP)", "TGF", "GF", "UNC", "FP"]

for ev_type in ev_type_list:
    df_catalog[ev_type] = False
    df_catalog.loc[idx_unknown, ev_type] = df_catalog.loc[idx_unknown, "catalog_triggers"].apply(
        lambda x: ev_type in str(x).replace("UNKNOWN: ", "").split("/")
    ).values
    dct_ev = {"GRB": "GRB", "SFL": "SF", "LOC": "UNC(LP)", "TRA": "UNC", "TGF": "TGF", "UNC": "UNC", "SGR": "UNC", "GAL": "GF", "DIS": "UNC"}
    df_catalog.loc[~idx_unknown, ev_type] = df_catalog.loc[~idx_unknown, "catalog_triggers"].apply(
        lambda x: ev_type == dct_ev.get(str(x)[:3], "UNC")
    ).values


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Builds spatial, detector, and spectral feature matrices."""
    base_cols = [
        "trig_dets", "sigma_r0", "sigma_r1", "sigma_r2", "duration",
        "ra", "dec", "ra_montecarlo", "dec_montecarlo", "ra_std", "dec_std",
        "ra_earth", "dec_earth", "earth_vis", "sun_vis", "ra_sun", "dec_sun",
        "l_galactic", "b_galactic", "lat_fermi", "lon_fermi", "alt_fermi", "l"
    ]
    available_base = [c for c in base_cols if c in df.columns]
    wavelet_cols = [c for c in df.columns if c.startswith("fe_")]
    
    X = df[available_base + wavelet_cols].copy().fillna(0.0)

    if "trig_dets" in X.columns:
        X["num_det_rng"] = X["trig_dets"].apply(lambda x: len(str(x).split()) if pd.notna(x) else 0)
        X["num_det"] = 0
        for det in ["n0", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "na", "nb"]:
            X[f"num_{det}"] = X["trig_dets"].apply(lambda x: 1 if det in str(x) else 0)
            X["num_det"] += X[f"num_{det}"]
        X.drop(columns=["trig_dets"], inplace=True)

    # Hardness Ratios
    safe_r0 = np.where(X.get("sigma_r0", 1.0) <= 0, 1e-4, X.get("sigma_r0", 1.0))
    safe_r1 = np.where(X.get("sigma_r1", 1.0) <= 0, 1e-4, X.get("sigma_r1", 1.0))
    X["HR10"] = np.minimum(X.get("sigma_r1", 0.0) / safe_r0, 10.0)
    X["HR21"] = np.minimum(X.get("sigma_r2", 0.0) / safe_r1, 10.0)

    # Angular distances
    ra_diff_sun = np.abs(X.get("ra", 0.0) - X.get("ra_sun", 0.0))
    dec_diff_sun = np.abs(X.get("dec", 0.0) - X.get("dec_sun", 0.0))
    X["diff_sun"] = np.minimum(ra_diff_sun, 360.0 - ra_diff_sun) + np.minimum(dec_diff_sun, 180.0 - dec_diff_sun)

    return X


X_feats = prepare_features(df_catalog).astype("float32")
X_feats.replace([np.inf, -np.inf], -1.0, inplace=True)
X_feats.fillna(-1.0, inplace=True)

# Multiclass target encoding: 1=GRB, 2=UNC(LP), 3=SF, 4=FP, 0=UNC
y_target = pd.Series(0, index=df_catalog.index)
y_target[df_catalog["GRB"]] = 1
y_target[df_catalog["UNC(LP)"]] = 2
y_target[df_catalog["SF"]] = 3
y_target[df_catalog["FP"]] = 4

X_train, X_test, y_train, y_test = train_test_split(
    X_feats, y_target, test_size=0.2, random_state=42, stratify=y_target
)

# Train Multiclass Random Forest Benchmark
rf_model = RandomForestClassifier(n_estimators=200, max_depth=5, class_weight="balanced", random_state=42)
rf_model.fit(X_train[y_train != 0], y_train[y_train != 0])
y_pred_test = rf_model.predict(X_test)

print("\n" + "=" * 60)
print("     SUPERVISED BENCHMARK PERFORMANCE (RANDOM FOREST)")
print("=" * 60)
print("Balanced Accuracy:", balanced_accuracy_score(y_test[y_test != 0], y_pred_test[y_test != 0]))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test[y_test != 0], y_pred_test[y_test != 0]))

# Feature importances
top_features = pd.Series(rf_model.feature_importances_, index=X_feats.columns).sort_values(ascending=False).head(10)
print("\nTop 10 Most Discriminant Physical Features:")
print(top_features)

# Save Decision Tree Visualization
dt_clf = tree.DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=42)
dt_clf.fit(X_train[y_train != 0], y_train[y_train != 0])

fig, ax = plt.subplots(figsize=(18, 10))
tree.plot_tree(dt_clf, filled=True, feature_names=list(X_feats.columns), ax=ax, fontsize=9)
dt_plot_path = DATA_DIR / "plots" / "decision_tree_benchmark.png"
fig.savefig(dt_plot_path, dpi=200, bbox_inches="tight")
plt.close(fig)
logging.info(f"Decision tree topology plot saved to: {dt_plot_path}")