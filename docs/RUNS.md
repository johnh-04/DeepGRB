# Run del motore

Generato da `python -m benchmark.report --index` (anche allo step 9 della pipeline): una riga per ogni run in `data/runs/` con un `manifest.json`. Valori letti dai file della run; "—" = step non eseguito o non applicabile.

| periodo | run | rete | eventi R/S/P | GBM rivelati | GRB | Crupi noti | Crupi inediti | senza controparte | loc/class | resoconto |
|---|---|---|---|---|---|---|---|---|---|---|
| 2019-03-01 → 2019-06-30 | `engine-v2` | `model_03-2019_07-2019_4.4_2026-09-21`, seed non registrato (modello legacy) | 144 (105/18/21) | 68/120 | 60/78 | 70/71 | 21/24 | 53 | ✔/✔ | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v2/RESULTS.md) |
| 2019-03-01 → 2019-06-30 | `engine-v2-seed1` | `model_2019-03-01_2019-06-30_seed1`, seed 1 | 136 (102/11/23) | 67/120 | 59/78 | 70/71 | 21/24 | 46 | —/— | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v2-seed1/RESULTS.md) |
| 2019-03-01 → 2019-06-30 | `engine-v2-sens-tmax29` | `model_03-2019_07-2019_4.4_2026-09-21`, seed non registrato (modello legacy) | 144 (105/18/21) | 68/120 | 60/78 | 70/71 | 21/24 | 53 | —/— | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v2-sens-tmax29/RESULTS.md) |
| 2019-03-01 → 2019-06-30 | `engine-v3` | `model_03-2019_07-2019_4.4_2026-09-21`, seed non registrato (modello legacy) | 144 (105/18/21) | 68/120 | 60/78 | 70/71 | 21/24 | 53 | ✔/✔ | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v3/RESULTS.md) |
| 2019-03-01 → 2019-06-30 | `engine-v3-seed1` | `model_2019-03-01_2019-06-30_seed1`, seed 1 | 136 (102/11/23) | 67/120 | 59/78 | 70/71 | 21/24 | 46 | ✔/✔ | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v3-seed1/RESULTS.md) |
| 2019-03-01 → 2019-06-30 | `engine-v3-verify1` | `model_2019-03-01_2019-06-30_verify1`, seed 1 | 136 (102/11/23) | 67/120 | 59/78 | 70/71 | 21/24 | 46 | ✔/✔ | [RESULTS.md](../data/runs/2019-03-01_2019-06-30/engine-v3-verify1/RESULTS.md) |
