# Consolidamento del framework DeepGRB — resoconto

> Documento in costruzione durante il consolidamento; la versione finale sostituisce questa.

## 2. Invarianti scientifici (registrati prima del refactoring)

Stato di partenza: branch `fix/baseline-2019`, commit `959dde0` (= tag `baseline-2019-validated` `4477ae2` + `docs/PROJECT_MAP.md`). Valori letti dai file con `sha256sum` e da `benchmark/out/<run>/REPORT.md`.

### 2.1 Checksum da riprodurre

| file | sha256 |
|---|---|
| `engine-v3-seed1/results/events_table.csv` | `eb0207fb7b96acef9c677b250a3f0f00503dacb18bf8d76e6d25db7cc02ed051` |
| `engine-v3-seed1/results/events_classified.csv` | `7924b0d67c200b9e15f40a100b8c153dd84d49fe500fb4113ecf968d692b86d0` |
| `engine-v3-seed1/results/triggers_table.csv` | `b430d5e70dc4be9fb83e79a335cc54f2beb6861ec0aa79810c73108523ffc474` |
| `engine-v3-seed1/results/events_table_loc.csv` | `0346fec93a02e9981acc9c1ce6e84031590b5665ae95ac645dfc1b1cc13fd418` |
| `engine-v3/results/events_table.csv` | `78f547180badac51e47061c6513bb5ed42a9e0b4f3763fb20671b7313dc32ae6` |
| `engine-v3/results/triggers_table.csv` | `e9bab9e930fc15f393be9e7dfcb51bb2f93aae8c3c15b081d582e20c520965cb` |

Controllo aggiuntivo (calcolo della validazione), da `benchmark/out/<run>/`:

| run | file | sha256 |
|---|---|---|
| v3-seed1 | matches_crupi_known.csv | `5f4c1891d40a58751b319df6001ee1109662966da04d7973bec7197da2176721` |
| v3-seed1 | matches_crupi_unknown.csv | `064710cf8beaef59a232ecb082a99468b201a14d63f81cf249198b29fa69d5e4` |
| v3-seed1 | matches_gbm_catalog.csv | `7677e5030eb663164453ddc7a0c547a58166d2905bf0bfe2a073fd184ba77c99` |
| v3-seed1 | events_flags.csv | `d83f587c271a8e893f6d388efd41898d83ba030cc3b7a78cc08fe44f2a6c517d` |
| v3 | matches_crupi_known.csv | `bc3cbc90d3b415dd84da726d9db9cd657dd0c51b2ed64988d743dc361d3688cd` |
| v3 | matches_crupi_unknown.csv | `01cc5a6d2115cbcadb457f606a88df135d5ce3ae1d73e668632cdb028974ae1c` |
| v3 | matches_gbm_catalog.csv | `e45ef7f968b086898d085fbe463b7d2595f51b78d46d1a079664d2b0e67d1f79` |
| v3 | events_flags.csv | `0016aff68c243d8a714eefa1db8f7ba4c6c2d508112dedca1cfc9bd6b6356d12` |

### 2.2 Numeri chiave da riprodurre

| run | eventi (R/S/P) | Crupi noti | Crupi inediti | inediti R+S | GBM rivelati/disponibili | GRB | T90 > 4.096 / ≤ 4.096 | senza controparte |
|---|---|---|---|---|---|---|---|---|
| engine-v3-seed1 (riferimento) | 136 (102/11/23) | 70/71 | 21/24 | 15/16 | 67/120 | 59/78 | 54/65 / 5/13 | 46 |
| engine-v3 (legacy) | 144 (105/18/21) | 70/71 | 21/24 | 15/16 | 68/120 | 60/78 | 54/65 / 6/13 | 53 |
