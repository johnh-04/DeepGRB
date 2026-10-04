"""
Population analysis of the 2019 baseline events (read-only on engine outputs).

For two runs of the same period, a reference (--run) and a comparison (--compare), e.g. the
2019 baseline engine-v2-seed1 (retrained network) and engine-v2 (legacy network):
  - groups: events matched to Crupi/GBM, and events without counterpart split by
    dist_saa_gap_s into A, B (bands below) and 'other';
  - one-to-one overlap of the two runs' events;
  - orbital position of every event from the POSHIST files: lat, lon, altitude, McIlwain L
    (gbm-data-tools), centred-dipole geomagnetic latitude, orbital phase (argument of
    latitude), signed time from SAA exit/entry (POSHIST flag) and from the data gaps, also
    one orbit earlier;
  - the same quantities for random valid times (null distribution);
  - KS tests, lat/lon map, table of the 'other' events with GBM catalog entries within 1 h.

Inputs: pred/, trig/, results/ and validation/ of both runs (pipeline steps 3-8).
Outputs: <reference run>/analysis/*.csv, *.png, summary.json (consumed by orbit_report.py).
Usage (repo root): python -m benchmark.analysis.orbit_analysis --run <reference run> --compare <comparison run>
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import fits
from gbm.data import PosHist
from scipy import stats

from benchmark.matching import overlap_one_to_one as _overlap
from connections.utils.config import DATA_DIR, FOLD_POSHIST, GBM_TRIG_DB, run_period
from utils.logs import detail, setup_logging
from utils.period import window_days

# set by configure(): the two runs ("ref" = reference, "cmp" = comparison), their period and the output folder
RUNS: Dict[str, Dict[str, Path]] = {}
OUT = Path()
START_DATE = END_DATE = ""


def configure(reference: Path, comparison: Path) -> None:
    """Points the module at two runs of the same period; outputs go to <reference>/analysis/."""
    global OUT, START_DATE, END_DATE
    reference, comparison = Path(reference).resolve(), Path(comparison).resolve()
    START_DATE, END_DATE = run_period(reference)
    if run_period(comparison) != (START_DATE, END_DATE):
        raise ValueError(f"{comparison.name} and {reference.name} cover different periods")
    RUNS.clear()
    RUNS.update({"cmp": {"run": comparison, "val": comparison / "validation"},
                 "ref": {"run": reference, "val": reference / "validation"}})
    OUT = reference / "analysis"


def add_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run", type=Path, required=True, help="reference run folder (e.g. the retrained network)")
    parser.add_argument("--compare", type=Path, required=True, help="comparison run folder of the same period")
BIN = 4.096
GAP_S = 500.0
# Bands of dist_saa_gap_s (s). They contain the two clusters observed in the 2019 baseline run with the
# retrained network (5091-5218 s, 5804-5837 s) with margins; the nearest values outside are 4981 s and 7000 s.
BANDS = {"A": (5050.0, 5300.0), "B": (5750.0, 5900.0)}
N_NULL = 5000
NULL_SEED = 12345
# Centred dipole pole (IGRF-13, epoch 2020): simple approximation, declared as such
DIPOLE_POLE_LAT, DIPOLE_POLE_LON = 80.65, -72.68
VARIABLES = ["lat", "lon", "alt_km", "L", "geomag_lat_dipole", "phase_deg",
             "t_since_saa_exit_s", "t_to_saa_entry_s", "prev_orbit_saa_offset_s",
             "t_since_gap_end_s", "t_to_gap_start_s", "dist_saa_region_deg"]


# ----------------------------------------------------------------------------- POSHIST
class Orbit:
    """All POSHIST samples of the window (+ neighbour days on disk), 1 Hz."""

    def __init__(self) -> None:
        days = window_days(START_DATE, END_DATE)
        lo = (pd.Timestamp(START_DATE) - pd.Timedelta(days=1)).strftime("%y%m%d")
        hi = (pd.Timestamp(END_DATE) + pd.Timedelta(days=1)).strftime("%y%m%d")
        files = []
        for d in [lo] + days + [hi]:
            f = sorted((DATA_DIR / FOLD_POSHIST).glob(f"glg_poshist_all_{d}_v*.fit"))
            if f:
                files.append((d, f[-1]))
        self.day_files = dict(files)
        parts = []
        for _, f in files:
            with fits.open(f, memmap=False) as h:
                d = h[1].data
                parts.append(pd.DataFrame({
                    "t": d["SCLK_UTC"].astype(float),
                    "x": d["POS_X"].astype(float), "y": d["POS_Y"].astype(float), "z": d["POS_Z"].astype(float),
                    "vx": d["VEL_X"].astype(float), "vy": d["VEL_Y"].astype(float), "vz": d["VEL_Z"].astype(float),
                    "lat": d["SC_LAT"].astype(float), "lon": d["SC_LON"].astype(float),
                    "saa": (d["FLAGS"] & 2) > 0,
                }))
        df = pd.concat(parts, ignore_index=True).sort_values("t").drop_duplicates("t").reset_index(drop=True)
        self.t = df["t"].to_numpy()
        self.df = df
        # SAA intervals (entry, exit) from the flag
        s = df["saa"].to_numpy().astype(int)
        edges = np.diff(s)
        entries = self.t[1:][edges == 1]
        exits = self.t[1:][edges == -1]
        if s[0] == 1:
            entries = np.r_[self.t[0], entries]
        if s[-1] == 1:
            exits = np.r_[exits, self.t[-1]]
        self.saa = np.c_[entries, exits]
        # orbital period from ascending-node crossings of the argument of latitude
        u = self.arg_latitude(np.arange(len(df))[::10])
        tt = self.t[::10]
        asc = tt[1:][np.diff(u) < -180]  # u wraps 360 -> 0 at the ascending node
        dt = np.diff(asc)
        self.period = float(np.median(dt[(dt > 5000) & (dt < 6500)]))
        # SAA region on the ground (subsample of flagged samples) for geographic distance
        self.saa_ground = df.loc[df["saa"], ["lat", "lon"]].iloc[::30].to_numpy()
        self._ph_cache: Dict[str, PosHist] = {}

    def idx(self, times: np.ndarray) -> np.ndarray:
        i = np.searchsorted(self.t, times)
        i = np.clip(i, 1, len(self.t) - 1)
        left_closer = np.abs(times - self.t[i - 1]) <= np.abs(self.t[i] - times)
        return np.where(left_closer, i - 1, i)

    def arg_latitude(self, rows: np.ndarray) -> np.ndarray:
        d = self.df.iloc[rows]
        r = d[["x", "y", "z"]].to_numpy()
        v = d[["vx", "vy", "vz"]].to_numpy()
        h = np.cross(r, v)
        n = np.cross(np.array([0.0, 0.0, 1.0]), h)
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        hn = h / np.linalg.norm(h, axis=1, keepdims=True)
        u = np.degrees(np.arctan2(np.einsum("ij,ij->i", np.cross(n, r), hn), np.einsum("ij,ij->i", n, r)))
        return np.mod(u, 360.0)

    def poshist(self, day: str) -> PosHist:
        if day not in self._ph_cache:
            self._ph_cache[day] = PosHist.open(str(self.day_files[day]))
        return self._ph_cache[day]

    def saa_signed(self, t: float) -> Tuple[float, float, float]:
        """(time since last SAA exit, time to next SAA entry, offset of t-P from the SAA interval).

        Offset convention: 0 inside the SAA one orbit earlier; negative = that many seconds
        before the entry; positive = after the exit.
        """
        en, ex = self.saa[:, 0], self.saa[:, 1]
        past = ex[ex <= t]
        fut = en[en >= t]
        since = t - past.max() if len(past) else np.nan
        to = fut.min() - t if len(fut) else np.nan
        tp = t - self.period
        inside = (en <= tp) & (tp <= ex)
        if inside.any():
            off = 0.0
        else:
            d_entry = tp - en  # negative before entry
            d_exit = tp - ex   # positive after exit
            cands = np.r_[d_entry[d_entry < 0], d_exit[d_exit > 0]]
            off = float(cands[np.argmin(np.abs(cands))]) if len(cands) else np.nan
        return since, to, off

    def describe(self, times: np.ndarray, days: List[str]) -> pd.DataFrame:
        rows = self.idx(times)
        u = self.arg_latitude(rows)
        lat, lon = self.df["lat"].to_numpy()[rows], self.df["lon"].to_numpy()[rows]
        out = []
        for k, (t, day) in enumerate(zip(times, days)):
            ph = self.poshist(day) if day in self.day_files else None
            since, to, off = self.saa_signed(t)
            out.append({
                "lat": lat[k], "lon": ((lon[k] + 180) % 360) - 180,
                "alt_km": float(ph.get_altitude(t)) / 1000 if ph is not None else np.nan,
                "L": float(ph.get_mcilwain_l(t)) if ph is not None else np.nan,
                "phase_deg": u[k],
                "t_since_saa_exit_s": since, "t_to_saa_entry_s": to, "prev_orbit_saa_offset_s": off,
            })
        df = pd.DataFrame(out)
        df["geomag_lat_dipole"] = dipole_latitude(df["lat"].to_numpy(), df["lon"].to_numpy())
        df["dist_saa_region_deg"] = [ground_distance(a, b, self.saa_ground) for a, b in zip(df["lat"], df["lon"])]
        return df


def dipole_latitude(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Centred-dipole geomagnetic latitude (simple approximation)."""
    la, lo = np.radians(lat), np.radians(lon)
    pla, plo = np.radians(DIPOLE_POLE_LAT), np.radians(DIPOLE_POLE_LON)
    s = np.sin(la) * np.sin(pla) + np.cos(la) * np.cos(pla) * np.cos(lo - plo)
    return np.degrees(np.arcsin(np.clip(s, -1, 1)))


def ground_distance(lat: float, lon: float, pts: np.ndarray) -> float:
    """Great-circle distance (deg) to the nearest ground position flagged as SAA; 0 inside."""
    la, lo = np.radians(lat), np.radians(lon)
    pla, plo = np.radians(pts[:, 0]), np.radians(pts[:, 1])
    c = np.sin(la) * np.sin(pla) + np.cos(la) * np.cos(pla) * np.cos(lo - plo)
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))).min())


# ----------------------------------------------------------------------------- runs
def data_gaps(frg_met: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """(gap start = last bin before, gap end = first bin after) for gaps > 500 s."""
    i = np.where(np.diff(frg_met) > GAP_S)[0]
    return frg_met[i], frg_met[i + 1]


def load_run(name: str) -> Tuple[pd.DataFrame, np.ndarray, pd.Series]:
    cfg = RUNS[name]
    ev = pd.read_csv(cfg["run"] / "results" / "events_table.csv")
    frg = pd.read_csv(cfg["run"] / "pred" / "frg.csv", usecols=["met", "timestamp", "n0_r1"])
    met = frg["met"].to_numpy(dtype=float)
    # t_start as in benchmark/validate.py: met of start_times_offset (first occurrence)
    ts_to_met = pd.Series(met, index=frg["timestamp"].values)
    ts_to_met = ts_to_met[~ts_to_met.index.duplicated(keep="first")]
    ev["t_start"] = ev["start_times_offset"].map(ts_to_met).fillna(ev["start_met"])

    lonely = pd.read_csv(cfg["val"] / "events_without_counterpart.csv")
    known = pd.read_csv(cfg["val"] / "matches_crupi_known.csv")
    unknown = pd.read_csv(cfg["val"] / "matches_crupi_unknown.csv")
    gbm = pd.read_csv(cfg["val"] / "matches_gbm_catalog.csv")
    ev["match_crupi_known"] = ev.index.isin(known.loc[known["matched"], "event"])
    ev["match_crupi_unknown"] = ev.index.isin(unknown.loc[unknown["matched"], "event"])
    ev["match_gbm"] = ev.index.isin(gbm.loc[gbm["matched"], "event"])
    ev["counterpart"] = ev["match_crupi_known"] | ev["match_crupi_unknown"] | ev["match_gbm"]
    ev = ev.merge(lonely[["trig_ids", "dist_saa_gap_s"]], on="trig_ids", how="left")

    # recompute dist_saa_gap_s with the validate.py definition (check)
    g0, g1 = data_gaps(met)
    edges = np.sort(np.r_[g0, g1])
    ev["dist_saa_gap_recomputed_s"] = [float(np.min(np.abs(edges - t))) for t in ev["t_start"]]

    def group(r):
        if r["counterpart"]:
            return "matched"
        for g, (a, b) in BANDS.items():
            if a <= r["dist_saa_gap_s"] <= b:
                return g
        return "other"
    ev["group"] = ev.apply(group, axis=1)
    ev["day"] = pd.to_datetime(ev["start_times"]).dt.strftime("%y%m%d")
    # signed distances from data gaps (gap end before t, gap start after t)
    ev["t_since_gap_end_s"] = [t - g1[g1 <= t].max() if (g1 <= t).any() else np.nan for t in ev["t_start"]]
    ev["t_to_gap_start_s"] = [g0[g0 >= t].min() - t if (g0 >= t).any() else np.nan for t in ev["t_start"]]
    valid_met = met[np.isfinite(frg["n0_r1"].to_numpy())]
    return ev, valid_met, frg["timestamp"]


def overlap_one_to_one(a: pd.DataFrame, b: pd.DataFrame, margin: float = 2 * BIN) -> List[Tuple[int, int, float]]:
    """Pairs of overlapping events of two runs (benchmark.matching.overlap_one_to_one)."""
    return _overlap(a["start_met"], a["duration"], b["start_met"], b["duration"], margin)


# ----------------------------------------------------------------------------- residuals
SHORT_PASSAGE_S = 500.0  # shorter SAA passages leave a data gap below the 500 s masking threshold
EDGE_WINDOW_S = 200.0
REGION_DEG = 3.5


def saa_distance_grid(orbit: "Orbit") -> np.ndarray:
    """Distance (deg) to the SAA-flagged ground region on a 1x1 deg grid (lat -30..30, lon -180..179)."""
    lats, lons = np.arange(-30, 31), np.arange(-180, 180)
    grid = np.empty((len(lats), len(lons)))
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            grid[i, j] = ground_distance(la, lo, orbit.saa_ground)
    return grid


def residual_by_zone(orbit: "Orbit", name: str, grid: np.ndarray) -> pd.DataFrame:
    """Summed-r1 relative residual (frg-bkg)/bkg and FOCuS r1 > 3 fraction per zone, all valid bins."""
    from utils.keys import get_keys
    keys = get_keys(rs=["1"])
    run = RUNS[name]["run"]
    frg = pd.read_csv(run / "pred" / "frg.csv", usecols=["met"] + keys)
    bkg = pd.read_csv(run / "pred" / "bkg.csv", usecols=keys)
    foc = pd.read_csv(run / "trig" / "trig.csv", usecols=keys)
    met = frg["met"].to_numpy(dtype=float)
    f, b = frg[keys].to_numpy(dtype=float), bkg[keys].to_numpy(dtype=float)
    valid = np.isfinite(f).all(axis=1) & np.isfinite(b).all(axis=1)
    rel = (np.nansum(f, axis=1) - np.nansum(b, axis=1)) / np.nansum(b, axis=1)
    trig = (foc.to_numpy(dtype=float) > 3.0).any(axis=1)

    en, ex = orbit.saa[:, 0], orbit.saa[:, 1]
    short = (ex - en) < SHORT_PASSAGE_S
    zone = np.full(len(met), "elsewhere", dtype=object)
    rows = orbit.idx(met)
    la = np.clip(np.round(orbit.df["lat"].to_numpy()[rows]), -30, 30).astype(int) + 30
    lo = (np.round(((orbit.df["lon"].to_numpy()[rows] + 180) % 360) - 180).astype(int) + 180) % 360
    zone[grid[la, lo] < REGION_DEG] = f"within {REGION_DEG} deg of SAA region"
    for e0, e1 in zip(en[short], ex[short]):
        zone[(met >= e0 - EDGE_WINDOW_S) & (met < e0)] = f"{EDGE_WINDOW_S:.0f} s before short passage"
        zone[(met > e1) & (met <= e1 + EDGE_WINDOW_S)] = f"{EDGE_WINDOW_S:.0f} s after short passage"
    out = []
    for z in [f"{EDGE_WINDOW_S:.0f} s before short passage", f"{EDGE_WINDOW_S:.0f} s after short passage",
              f"within {REGION_DEG} deg of SAA region", "elsewhere"]:
        m = valid & (zone == z)
        out.append({"run": name, "zone": z, "valid_bins": int(m.sum()),
                    "median_rel_residual_%": 100 * float(np.median(rel[m])) if m.any() else np.nan,
                    "p90_rel_residual_%": 100 * float(np.percentile(rel[m], 90)) if m.any() else np.nan,
                    "frac_bins_focus_r1_gt3_%": 100 * float(trig[m].mean()) if m.any() else np.nan})
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_cli(parser)
    args = parser.parse_args()
    setup_logging()
    configure(args.run, args.compare)
    OUT.mkdir(parents=True, exist_ok=True)
    orbit = Orbit()
    summary = {"orbital_period_s": orbit.period, "n_saa_passages": int(len(orbit.saa)), "bands": BANDS,
               "dipole_pole": [DIPOLE_POLE_LAT, DIPOLE_POLE_LON], "runs": {}}

    events = {}
    valid_met = None
    for name in RUNS:
        ev, vm, _ = load_run(name)
        geo = orbit.describe(ev["t_start"].to_numpy(), ev["day"].tolist())
        ev = pd.concat([ev.reset_index(drop=True), geo], axis=1)
        ev["run"] = name
        events[name] = ev
        valid_met = vm if valid_met is None else valid_met
        lone = ev[~ev["counterpart"]]
        summary["runs"][name] = {
            "events": int(len(ev)), "without_counterpart": int(len(lone)),
            "groups": ev["group"].value_counts().to_dict(),
            "dist_check_max_abs_diff_s": float(np.nanmax(np.abs(lone["dist_saa_gap_s"] - lone["dist_saa_gap_recomputed_s"]))),
        }
        ev.to_csv(OUT / f"events_orbit_{name}.csv", index=False)

    # null distribution: random valid bins
    rng = np.random.default_rng(NULL_SEED)
    t_null = np.sort(rng.choice(valid_met, size=N_NULL, replace=False))
    days_null = [pd.Timestamp("2001-01-01") + pd.Timedelta(seconds=float(t)) for t in t_null]
    days_null = [d.strftime("%y%m%d") for d in days_null]  # MET->UTC within a few s: day only
    null = orbit.describe(t_null, days_null)
    v2 = events["cmp"]
    g0 = v2  # gaps identical across runs (same data rows)
    frg_met = pd.read_csv(RUNS["cmp"]["run"] / "pred" / "frg.csv", usecols=["met"])["met"].to_numpy(dtype=float)
    gs, ge = data_gaps(frg_met)
    null["t_since_gap_end_s"] = [t - ge[ge <= t].max() if (ge <= t).any() else np.nan for t in t_null]
    null["t_to_gap_start_s"] = [gs[gs >= t].min() - t if (gs >= t).any() else np.nan for t in t_null]
    edges = np.sort(np.r_[gs, ge])
    null["dist_saa_gap_s"] = [float(np.min(np.abs(edges - t))) for t in t_null]
    null["group"] = "null"
    null.to_csv(OUT / "null_orbit.csv", index=False)

    # KS tests: each group vs matched and vs null, per run
    ks_rows = []
    for name, ev in events.items():
        for g in ["A", "B", "other"]:
            sub = ev[ev["group"] == g]
            if len(sub) < 3:
                continue
            for ref_name, ref in (("matched", ev[ev["group"] == "matched"]), ("null", null)):
                for v in VARIABLES:
                    x, y = sub[v].dropna(), ref[v].dropna()
                    if len(x) >= 3 and len(y) >= 3:
                        r = stats.ks_2samp(x, y)
                        ks_rows.append({"run": name, "group": g, "n": len(x), "vs": ref_name, "variable": v,
                                        "median_group": float(x.median()), "median_ref": float(y.median()),
                                        "ks_D": float(r.statistic), "p_value": float(r.pvalue)})
    pd.DataFrame(ks_rows).to_csv(OUT / "ks_tests.csv", index=False)

    # Key fractions: one orbit earlier inside/near the SAA, and dist_saa_gap band occupancy in the null
    frac = []
    for name, ev in events.items():
        for g in ["matched", "A", "B", "other"]:
            sub = ev[ev["group"] == g]
            if len(sub):
                frac.append({"run": name, "group": g, "n": len(sub),
                             "prev_orbit_in_saa": int((sub["prev_orbit_saa_offset_s"] == 0).sum()),
                             "prev_orbit_within_300s": int((sub["prev_orbit_saa_offset_s"].abs() <= 300).sum()),
                             "next_saa_entry_within_1_orbit": int((sub["t_to_saa_entry_s"] <= orbit.period).sum())})
    frac.append({"run": "null", "group": "null", "n": len(null),
                 "prev_orbit_in_saa": int((null["prev_orbit_saa_offset_s"] == 0).sum()),
                 "prev_orbit_within_300s": int((null["prev_orbit_saa_offset_s"].abs() <= 300).sum()),
                 "next_saa_entry_within_1_orbit": int((null["t_to_saa_entry_s"] <= orbit.period).sum())})
    for g, (a, b) in BANDS.items():
        summary[f"null_fraction_in_band_{g}"] = float(((null["dist_saa_gap_s"] >= a) & (null["dist_saa_gap_s"] <= b)).mean())
    pd.DataFrame(frac).to_csv(OUT / "saa_fractions.csv", index=False)

    # Binomial probability of the observed band occupancy among events without counterpart
    for name, ev in events.items():
        lone = ev[~ev["counterpart"]]
        for g, (a, b) in BANDS.items():
            k = int(((lone["dist_saa_gap_s"] >= a) & (lone["dist_saa_gap_s"] <= b)).sum())
            p0 = summary[f"null_fraction_in_band_{g}"]
            summary["runs"][name][f"band_{g}_count"] = k
            summary["runs"][name][f"band_{g}_binom_p"] = float(stats.binomtest(k, len(lone), p0, alternative="greater").pvalue)
            mk = ev[ev["counterpart"]]
            summary["runs"][name][f"band_{g}_matched_count"] = int(((mk["dist_saa_gap_recomputed_s"] >= a) & (mk["dist_saa_gap_recomputed_s"] <= b)).sum())
            summary["runs"][name]["matched_n"] = int(len(mk))

    # Overlap between runs
    a, b = events["cmp"], events["ref"]
    pairs = overlap_one_to_one(a, b)
    pa = {i: j for i, j, _ in pairs}
    pb = {j: i for i, j, _ in pairs}
    a["pair_ref"] = [b["trig_ids"].iat[pa[i]] if i in pa else -1 for i in range(len(a))]
    b["pair_cmp"] = [a["trig_ids"].iat[pb[j]] if j in pb else -1 for j in range(len(b))]
    a["pair_group"] = [b["group"].iat[pa[i]] if i in pa else "absent" for i in range(len(a))]
    b["pair_group"] = [a["group"].iat[pb[j]] if j in pb else "absent" for j in range(len(b))]
    cross = pd.crosstab(pd.Categorical(a["group"], ["matched", "A", "B", "other"]),
                        pd.Categorical(a["pair_group"], ["matched", "A", "B", "other", "absent"]), dropna=False)
    cross_b = b.loc[b["pair_cmp"] < 0, "group"].value_counts().reindex(["matched", "A", "B", "other"]).fillna(0).astype(int)
    cross.to_csv(OUT / "overlap_cmp_rows_vs_ref_cols.csv")
    summary["overlap"] = {"pairs": len(pairs), "only_cmp": int((a["pair_ref"] < 0).sum()),
                          "only_ref": int((b["pair_cmp"] < 0).sum()),
                          "only_ref_by_group": cross_b.to_dict(),
                          "median_abs_dstart_s": float(np.median([d for _, _, d in pairs])) if pairs else None}
    a.to_csv(OUT / "events_orbit_cmp.csv", index=False)
    b.to_csv(OUT / "events_orbit_ref.csv", index=False)

    # 'other' events of the reference run with GBM catalog entries within 1 h
    cat = pd.read_csv(GBM_TRIG_DB)
    oth = b[b["group"] == "other"].copy()
    gbm_near = []
    for t in oth["start_met"]:
        near = cat[(cat["trig_met"] - t).abs() <= 3600].sort_values("trig_met")
        gbm_near.append("; ".join(f"{r['name']} ({r['trigger_type']}, {r['trig_met'] - t:+.0f} s)" for _, r in near.iterrows()) or "-")
    oth["gbm_within_1h"] = gbm_near
    cols = ["trig_ids", "start_times", "duration", "detectors", "sigma_r0", "sigma_r1", "sigma_r2", "sigma_C", "CE",
            "lat", "lon", "alt_km", "L", "phase_deg", "t_since_saa_exit_s", "t_to_saa_entry_s",
            "prev_orbit_saa_offset_s", "dist_saa_gap_s", "pair_cmp", "pair_group", "gbm_within_1h"]
    oth[cols].to_csv(OUT / "others_ref.csv", index=False)

    # Map
    colors = {"matched": ("black", 12, "abbinati Crupi/GBM"), "A": ("tab:red", 40, "senza controparte A"),
              "B": ("tab:blue", 40, "senza controparte B"), "other": ("tab:green", 40, "senza controparte altri")}
    fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
    for ax, name in zip(axes, ["ref", "cmp"]):
        ax.scatter(((orbit.saa_ground[:, 1] + 180) % 360) - 180, orbit.saa_ground[:, 0], s=1, c="0.85", label="campioni POSHIST in SAA")
        ax.scatter(null["lon"], null["lat"], s=1, c="0.6", alpha=0.3, label="tempi casuali validi")
        ev = events[name]
        for g, (c, sz, lab) in colors.items():
            sub = ev[ev["group"] == g]
            ax.scatter(sub["lon"], sub["lat"], s=sz, c=c, label=f"{lab} ({len(sub)})", edgecolors="none" if g == "matched" else "k")
        ax.set_title(f"{RUNS[name]['run'].name}: posizione di Fermi all'inizio dell'evento")
        ax.set_ylabel("latitudine [deg]")
        ax.set_xlim(-180, 180)
        ax.set_ylim(-30, 30)
        ax.grid(alpha=0.3)
        ax.legend(loc="lower left", fontsize=8, markerscale=1.5)
    axes[-1].set_xlabel("longitudine [deg]")
    fig.tight_layout()
    fig.savefig(OUT / "map_lat_lon.png", dpi=130)
    plt.close(fig)

    # Histogram of time since SAA exit, in orbits
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bins = np.arange(0, 6.01, 0.1)
    ax.hist(null["t_since_saa_exit_s"] / orbit.period, bins=bins, density=True, color="0.7", label="tempi casuali validi")
    for g, c in (("matched", "black"), ("A", "tab:red"), ("B", "tab:blue"), ("other", "tab:green")):
        sub = events["ref"].loc[events["ref"]["group"] == g, "t_since_saa_exit_s"] / orbit.period
        ax.hist(sub, bins=bins, density=True, histtype="step", lw=2, color=c, label=f"{R} {g} ({len(sub)})")
    ax.set_xlabel("tempo dall'ultima uscita dalla SAA [orbite]")
    ax.set_ylabel("densità")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "hist_time_since_saa_exit.png", dpi=130)
    plt.close(fig)

    # residuals per zone (does the network underestimate the background there?)
    grid = saa_distance_grid(orbit)
    pd.concat([residual_by_zone(orbit, n, grid) for n in RUNS], ignore_index=True).to_csv(OUT / "residual_by_zone.csv", index=False)
    en, ex = orbit.saa[:, 0], orbit.saa[:, 1]
    short = (ex - en) < SHORT_PASSAGE_S
    summary["short_passages"] = int(short.sum())
    summary["short_passage_duration_s"] = [float((ex - en)[short].min()), float(np.median((ex - en)[short])), float((ex - en)[short].max())]
    for name, ev in events.items():
        lone = ev[~ev["counterpart"]]
        hit = [bool(((lone["t_start"] >= e0 - EDGE_WINDOW_S) & (lone["t_start"] < e0)).any()) for e0 in en[short]]
        summary["runs"][name]["short_passages_preceded_by_event_without_counterpart"] = int(sum(hit))
        summary["runs"][name]["A_before_short_passage"] = int(sum(
            bool(((en[short] - t) > 0).any() and (en[short][en[short] > t].min() - t) <= EDGE_WINDOW_S)
            for t in ev.loc[ev["group"] == "A", "t_start"]))
    summary["null_within_region_%"] = float(100 * (null["dist_saa_region_deg"] < REGION_DEG).mean())
    g_lat, g_lon = orbit.saa_ground[:, 0], ((orbit.saa_ground[:, 1] + 180) % 360) - 180
    summary["saa_region"] = {"lat_min": float(g_lat.min()), "lat_max": float(g_lat.max()),
                             "lon_min": float(g_lon.min()), "lon_max": float(g_lon.max())}
    band = np.abs(g_lat - (-12.0)) < 1.0
    summary["saa_region"]["lon_range_at_lat_-12"] = [float(g_lon[band].min()), float(g_lon[band].max())]

    # Zero predicted background: FOCuS treats it as invalid, analyze.event_significance does not
    from utils.keys import get_keys
    for name, ev in events.items():
        bk = pd.read_csv(RUNS[name]["run"] / "pred" / "bkg.csv", usecols=get_keys()).to_numpy(dtype=float)
        zero_rows = np.where((bk <= 0).any(axis=1))[0]
        ts = pd.read_csv(RUNS[name]["run"] / "pred" / "frg.csv", usecols=["timestamp"])["timestamp"]
        pos = pd.Series(np.arange(len(ts)), index=ts.values)
        pos = pos[~pos.index.duplicated(keep="first")]
        inside, adjacent = [], []
        for _, r in ev.iterrows():
            s0, s1 = int(pos[r["start_times_offset"]]), int(r["end_index"]) - 1  # window of S (offset start .. last bin)
            if ((zero_rows >= s0) & (zero_rows <= s1)).any():
                inside.append(int(r["trig_ids"]))
            elif len(zero_rows) and min(np.abs(zero_rows - s0).min(), np.abs(zero_rows - s1).min()) <= 1:
                adjacent.append(int(r["trig_ids"]))
        summary["runs"][name]["zero_bkg_cells"] = int((bk <= 0).sum())
        summary["runs"][name]["zero_bkg_rows"] = int(len(zero_rows))
        summary["runs"][name]["events_zero_bkg_inside_S_window"] = inside
        summary["runs"][name]["events_zero_bkg_adjacent_1bin"] = adjacent
    # High-L summary (all groups and null)
    summary["high_L_threshold"] = 1.4
    for name, ev in events.items():
        summary["runs"][name]["L_ge_1.4_by_group"] = {g: [int((ev.loc[ev["group"] == g, "L"] >= 1.4).sum()), int((ev["group"] == g).sum())]
                                                     for g in ["matched", "A", "B", "other"]}
    summary["null_L_ge_1.4_%"] = float(100 * (null["L"] >= 1.4).mean())

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    detail(f"written {OUT}")


if __name__ == "__main__":
    main()
