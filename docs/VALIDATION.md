# Validation method

Steps 8-9 of the pipeline (`validation/validate.py`, `validation/report.py`) compare the events of a run with two
references, kept separate:

- **A. Official Fermi-GBM catalogs.** The trigger catalog (HEASARC fermigtrig, `data/gbm_trig_catalog.csv`) with every
  trigger type (GRB, SFLARE, TGF, LOCLPAR, UNCERT, …), and the Burst Catalog (`data/gbm_burst_catalog.db`) for the GRB
  durations T90. They measure what the pipeline finds of what Fermi already saw. Always computed.
- **B. Crupi et al. (2023).** Table 11 (events with a GBM counterpart, "known") and Table 10 (events without a GBM
  counterpart, "unknown"), in `validation/reference/`. They measure how well the paper is reproduced, unknown events
  included. Computed when the run period overlaps the period of the paper (2019-03-01 → 2019-07-09).

## Matching

- **One-to-one**: an event matches at most one reference and vice versa; candidate pairs are assigned by increasing
  distance (`validation/matching.py`). References without a time are kept as unmatched.
- **Primary window**: a reference is matched when its time falls in [event start − 2 bins, event end + 2 bins]
  (± 8.192 s). The event start is the FOCuS change point.
- **Sensitivity**: the same statistics with ±10 s, ±60 s and ±1200 s. Wide windows create false matches with events of
  4–100 s and are reported only as sensitivity.
- A GBM trigger counts as available only if valid data (not masked, not in a gap) exist at its time; the others are
  reported as "no data" (the paper counts them as missing).
- Unmatched references get a diagnosis: no data, close to an SAA gap, FOCuS below threshold, or detected but merged into
  an event already matched to another reference.

## Acceptance criteria

Targets on the 2019 period (Crupi's tables restricted to 2019-03-01 → 2019-06-30: 71 known and 24 unknown events), not
thresholds to tune for:

- at least 90% of Crupi's known events found, and all known R and S events;
- at least 90% of the unknown R+S events found;
- at least 70% of all unknown events found, the missing P events explained;
- GRB recall with T90 > 4.096 s of the order of 88% and with T90 ≤ 4.096 s of the order of 34% (figures of the paper up to
  2019-07-09: order-of-magnitude comparison);
- number of events of the order of 100 (informative: it depends on the network).

When a criterion is not met, the answer is a per-event diagnosis (background, σ, SAA, clustering), never a change of
parameters. The tier of an event follows the paper: R (robust) several detectors and several energy ranges, S (solid)
several detectors in one range, P (probable) the others.

## Events without counterpart

Events matched neither to the GBM catalog nor to Crupi's tables are listed with their distance from the nearest SAA gap,
the nearest Crupi event and the post-processing flags (`models/flags.py`):

- `saa_edge_short_passage`: the event starts within 200 s before the entry or after the exit of an SAA passage whose data
  gap is ≤ 500 s, hence not masked;
- `saa_region_proximity`: Fermi is within 3.5° of the region where the POSHIST SAA flag is set;
- `near_zero_prediction`: the event, extended by 5 bins, touches a bin where the predicted background is ≤ 0.

The flags add columns and never remove events. Events without counterpart are candidates, not discoveries.

## Two classification matrices

They answer different questions and must not be confused.

1. **Predicted class against Crupi's tentative classes** (events matched to Crupi). Crupi's classes were assigned by hand
   and are tentative, sometimes multiple (`GRB/GF`). The confusion matrix uses the events with a single class and reports
   counts, row percentages (recall), column percentages (precision), per-class recall, precision and support, and the
   overall accuracy; each rule is also evaluated one-vs-rest, as in Crupi's script.
2. **GBM trigger type against predicted class** (GBM triggers matched to an event). The GBM type is the label of the
   flight software and of the duty scientists, not the physical nature of the event. The agreement is computed with a
   mapping declared as a hypothesis: GRB→GRB, SFLARE→SF, TGF→TGF, LOCLPAR→UNC(LP), UNCERT→UNC. Before the join, every
   matched trigger is checked to fall in the window of the event it points to.

The classifier never reads catalog columns: the catalog is used only to evaluate it.

## Limits

- Crupi's tables cover 2019-03-01 → 2019-07-09; the four reference events of July are out of the 2019 baseline.
- The paper reports 100 events but its tables list 99 (74 known + 25 unknown).
- The paper figures for the GBM catalog include July: comparisons are of order of magnitude.
- The localization is not compared with reference positions.
- The classifier misses Crupi's FP rule and the light-curve features `fe_*`; it is weak outside GRBs.
