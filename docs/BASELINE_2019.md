# Baseline 2019 — documento di riferimento

Generato da `python -m benchmark.baseline_doc` (codice al commit `dcd72b0`, branch `fix/baseline-2019`). Numeri, metadati e checksum letti dai file; nessuna cifra scritta a mano.

## 1. Riferimento

- Periodo: 2019-03-01 → 2019-06-30 (inclusivo). Motore: engine v3 (v3 = v2 con S che ignora i bin con fondo previsto ≤ 0).
- **Run di riferimento**: `data/runs/2019-03-01_2019-06-30/engine-v3-seed1`; step 5 eseguito dal commit `94f2a21`, predizioni e trigger riusati da `data/runs/2019-03-01_2019-06-30/engine-v2-seed1` (prodotti dal commit `c244881`).
- **Run di confronto (rete legacy)**: `data/runs/2019-03-01_2019-06-30/engine-v3`, predizioni da `data/runs/2019-03-01_2019-06-30/engine-v2`.
- **Rete di riferimento**: `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1`
  - seed 1; periodo 2019-03-01 → 2019-06-30; addestrata il 2026-10-04T07:44:31 dal commit `c244881`;
  - iperparametri: loss_type=mean, units=2048, epochs=64, lr=0.0008, batch_size=2048, dropout=0.02, validation_split=0.3, split_seed=0;
  - righe fit/validazione/test: 1164300/498987/554429; epoche 64, migliore 57; tempo di fit 6.3 min su /physical_device:GPU:0;
  - MAE di test media sui 36 canali 4.383; controllo di convergenza: assente (training precedente al controllo; riferimento: val_loss migliore 4.39 contro 20.4 del predittore costante per canale, `benchmark/analysis/out/lr_check.json`);
  - versioni: python 3.9.23, tensorflow 2.20.0, keras 3.10.0, numpy 1.26.4, pandas 1.5.3, sklearn 1.6.1.
- **Rete legacy**: `data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21` (trained by upstream-equivalent code (b0b2802); scaler refitted with split_seed).

## 2. Riproduzione

Dalla radice del repo, env `deepgrb_recas`. Download e preprocess devono essere completi (`python -m benchmark.audit.data_inventory`).

```bash
# a) Riferimento seed1 a partire dagli artefatti esistenti (riusa pred/ e trig/ di engine-v2-seed1; nessun training)
DEEPGRB_RUN_LABEL=seed1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py
python -m benchmark.classify --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --jobs 4
python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v3-seed1 --out benchmark/out/v3-seed1

# b) Confronto con la rete legacy (riusa pred/ e trig/ di engine-v2)
DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py
python -m benchmark.validate --run data/runs/2019-03-01_2019-06-30/engine-v3 --out benchmark/out/v3

# c) Da zero, nuovo training (cartelle e bundle non devono esistere; GPU consigliata)
DEEPGRB_RUN_LABEL=seed1 DEEPGRB_TRAIN_SEED=1 DEEPGRB_FORCE_TRAIN=1 DEEPGRB_SKIP_DOWNLOAD=1 python -u pipeline/pipeline_bkg.py
```

Le cartelle di run etichettate non vengono mai sovrascritte: per ripetere a) o c) spostare prima la cartella esistente in `data/_archive_<data>/`. Un nuovo training (c) **non** riproduce i pesi bit a bit (su GPU TensorFlow non è deterministico): i numeri di questo documento sono riproducibili esattamente solo a partire dal bundle di riferimento (checksum in §6).

## 3. Numeri chiave

| run | eventi | CE R/S/P | Crupi noti | Crupi inediti | inediti R+S | GBM rivelati/disponibili | GRB | T90>4.096 / ≤4.096 | senza controparte | flaggati: abbinati / senza controparte | classe compatibile con Crupi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 legacy (`engine-v2`) | 144 | 105/18/21 | 70/71 | 21/24 | 15/16 | 68/120 | 60/78 | 54/65 / 6/13 | 53 | — | 79/91 |
| v2 seed1 (`engine-v2-seed1`) | 136 | 102/11/23 | 70/71 | 21/24 | 15/16 | 67/120 | 59/78 | 54/65 / 5/13 | 46 | — | — |
| v3 seed1 (riferimento) (`engine-v3-seed1`) | 136 | 102/11/23 | 70/71 | 21/24 | 15/16 | 67/120 | 59/78 | 54/65 / 5/13 | 46 | 1/90 / 31/46 | 79/91 |
| v3 legacy (`engine-v3`) | 144 | 105/18/21 | 70/71 | 21/24 | 15/16 | 68/120 | 60/78 | 54/65 / 6/13 | 53 | 1/91 / 38/53 | — |

Regola di abbinamento: uno-a-uno, istante del riferimento entro [inizio evento − 2 bin, fine evento + 2 bin] (`benchmark/matching.py`). Il paper (fino al 9 luglio) riporta 100 eventi, GRB 65/81, T90 > 4.096 s 60/68, T90 ≤ 4.096 s 5/13. Le run v2 sono state validate prima dell'introduzione dei flag ("—"); i loro eventi coincidono con quelli delle v3 (salvo S dell'evento 6 di seed1).

## 4. Flag di post-processing (`models/saa_flags.py`; non cambiano l'elenco degli eventi)

- `saa_edge_short_passage`: l'inizio dell'evento (change point FOCuS) cade entro 200 s prima dell'entrata o dopo l'uscita di un passaggio SAA (flag POSHIST) il cui buco nei dati è ≤ 500 s, quindi **non mascherato** dallo step 3.
- `saa_region_proximity`: la posizione di Fermi all'inizio dell'evento è entro 3.5° dalla regione con flag SAA nelle POSHIST (regione campionata su griglia di 0.1°).
- `near_zero_prediction`: i bin dell'evento, estesi di 5 per lato, toccano un bin con fondo previsto ≤ 0. Nella run di riferimento: eventi [6, 9].

Per evento: `benchmark/out/<run>/events_flags.csv`. Analisi che li motiva: `docs/ORBIT_ANALYSIS.md`.

## 5. Limiti noti e perimetro

- **Passaggi SAA brevi non mascherati** (gruppo A di ORBIT_ANALYSIS): la maschera agisce solo sui buchi > 500 s; prima dei passaggi brevi la rete sottostima il fondo. Eventi con `saa_edge_short_passage` nel riferimento: 17, di cui abbinati a Crupi/GBM 0.
- **Bordo nord della SAA** (gruppo B): eventi senza controparte vicini alla regione SAA, nell'orbita che precede il primo passaggio di una sequenza. Senza controparte con `saa_region_proximity` e senza `saa_edge_short_passage`: 12.
- **Celle con fondo previsto 0** (rete seed1): 212 celle in 6 bin; la rete è instabile dove la velocità angolare (w1, w2, w3) è nella coda estrema della distribuzione: la pre-attivazione finale diventa negativa e la ReLU taglia a zero (ORBIT_ANALYSIS §5b). Da engine v3 quei bin sono esclusi da S; gli eventi adiacenti ([6, 9]) restano e sono marcati da `near_zero_prediction`.
- **Rivelatore nb**: compare in 34/46 eventi senza controparte contro 49/90 abbinati a Crupi/GBM; i residui di nb_r1 non sono distorti più degli altri canali (ORBIT_ANALYSIS e report). Causa non determinata.
- **Dipendenza dalla rete**: lo stesso codice con due addestramenti dà 144 (legacy) e 136 (seed1) eventi; 126 coppie in comune (abbinamento uno-a-uno degli intervalli ±2 bin); eventi abbinati a Crupi/GBM: 91 legacy, 90 seed1, tutti in coppia tra loro: sì. Cambiano gli eventi senza controparte.
- **Localizzazione** (dentro `benchmark.classify`): eseguita e deterministica (seed per evento; seriale = parallela), ma **non validata** contro le posizioni dei cataloghi (GBM o Crupi). RA/Dec, distanze da Sole e Terra e le classi che ne dipendono vanno usate con cautela.
- **Classificatore**: baseline euristica di Crupi (soglie da decision tree rifinite a mano); mancano la regola FP e le feature `fe_*` (tsfel).
- **Scelte paper ↔ codice** (docs/WORKING_RULES.md §2): FOCuS sui rate, esclusione SAA ±150 bin, t_max 50 bin (codice upstream); confronto col paper fino al 9 luglio solo come ordine di grandezza.

## 6. Checksum sha256

| file | sha256 |
|---|---|
| data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/metadata.json | 84e696e028442011e696c548be9337a7915c312ac326a2fcadd4923b636feb21 |
| data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/model.keras | b29f1e5579cdd9d3065b918eef84fe3f7590cd39fc60fdc086abeb910b7d04c3 |
| data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/scaler.joblib | 65820d5e57b12fe23119562e6cbf5752fefe6412f5487e6c8debf3f919d35908 |
| data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21/metadata.json | 8c1ca4852649568ac1e499042e5bf22befcf662c3cc8c375bd889c6f1b55a8b2 |
| data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21/model.h5 | 80986ab9f1e552cb7fe83c354a4d7da93d3b663189d5de38c9338ec9d30d7dee |
| data/nn_model/bundles/model_03-2019_07-2019_4.4_2026-09-21/scaler.joblib | 65820d5e57b12fe23119562e6cbf5752fefe6412f5487e6c8debf3f919d35908 |
| data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_table.csv | eb0207fb7b96acef9c677b250a3f0f00503dacb18bf8d76e6d25db7cc02ed051 |
| data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/triggers_table.csv | b430d5e70dc4be9fb83e79a335cc54f2beb6861ec0aa79810c73108523ffc474 |
| data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_table_loc.csv | 0346fec93a02e9981acc9c1ce6e84031590b5665ae95ac645dfc1b1cc13fd418 |
| data/runs/2019-03-01_2019-06-30/engine-v3-seed1/results/events_classified.csv | 7924b0d67c200b9e15f40a100b8c153dd84d49fe500fb4113ecf968d692b86d0 |
| data/runs/2019-03-01_2019-06-30/engine-v3/results/events_table.csv | 78f547180badac51e47061c6513bb5ed42a9e0b4f3763fb20671b7313dc32ae6 |
| data/runs/2019-03-01_2019-06-30/engine-v3/results/triggers_table.csv | e9bab9e930fc15f393be9e7dfcb51bb2f93aae8c3c15b081d582e20c520965cb |
| data/runs/2019-03-01_2019-06-30/engine-v2-seed1/results/events_table.csv | 64af06bd10cb8fecad6bccee16939a1d315843fd1bfb9aee61d80cfe480eccf0 |
| data/runs/2019-03-01_2019-06-30/engine-v2-seed1/results/triggers_table.csv | b430d5e70dc4be9fb83e79a335cc54f2beb6861ec0aa79810c73108523ffc474 |
| data/runs/2019-03-01_2019-06-30/engine-v2/results/events_table.csv | 78f547180badac51e47061c6513bb5ed42a9e0b4f3763fb20671b7313dc32ae6 |
| data/runs/2019-03-01_2019-06-30/engine-v2/results/triggers_table.csv | e9bab9e930fc15f393be9e7dfcb51bb2f93aae8c3c15b081d582e20c520965cb |
| data/runs/2019-03-01_2019-06-30/engine-v2/results/events_table_loc.csv | 3b937f0e71b8ad74d89ea5a0e83e4d380fd889752cb1f3a32e67e84733fbcfb3 |
| data/runs/2019-03-01_2019-06-30/engine-v2/results/events_classified.csv | ccb16d8b170bc0e13a354884b0a4446903fa8ad452471cdbf4d32bab20c67312 |

## 7. Cosa è versionato e cosa no

- Versionati: codice, documenti, `benchmark/out/v3-seed1/` e `benchmark/out/v3/` (REPORT.md e CSV), metadati e scaler dei bundle già tracciati.
- **Non versionati** (pesanti o derivati, presenti solo su disco): `data/runs/*/pred/`, `data/runs/*/trig/` (matrici, ~2.7 GB per run); le cartelle `data/runs/*/engine-v2-seed1/`, `engine-v3/`, `engine-v3-seed1/` (results, manifest e i symlink `pred`/`trig` delle v3 verso le v2); il bundle `data/nn_model/bundles/model_2019-03-01_2019-06-30_seed1/` (pesi, scaler, metadata); `benchmark/out/seed1/`; `benchmark/analysis/out/`; `logs/`; `data/_archive_*/` (salvo README e checksum). Le run v3 dipendono dalle v2 tramite symlink: spostare o cancellare una run v2 rompe la v3 corrispondente.
