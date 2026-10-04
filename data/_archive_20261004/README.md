# Archivio 2026-10-04 (consolidamento)

Run spostate (non cancellate) per la prova di invarianza del consolidamento (docs/REFACTOR_REPORT.md §2):
la pipeline consolidata ha rigenerato gli step 5-9 di `engine-v3-seed1` ed `engine-v3` riusando pred/ e trig/
delle run engine-v2 (symlink); i checksum dei file rigenerati sono confrontati con quelli di queste copie.

- `engine-v3-seed1/`: run di riferimento della baseline 2019 al tag `baseline-2019-validated` (pred/ e trig/ sono symlink a `engine-v2-seed1`).
- `engine-v3/`: run con la rete legacy allo stesso tag (symlink a `engine-v2`).
- `intermediate/engine-v3-seed1/`, `intermediate/engine-v3/`: prima rigenerazione con la pipeline consolidata (commit `bf188c2`, poi riscritto dal rebase locale in `8c1ba6b` con lo stesso codice); stessi checksum delle run al tag. Spostate per rigenerare le run con il codice finale del consolidamento.
