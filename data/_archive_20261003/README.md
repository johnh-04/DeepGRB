# Archivio 2026-10-03 (Fase 0)

Congelamento dello stato prima di qualunque correzione. **Copia**, non spostamento: gli originali restano al loro posto, perché spostarli cambierebbe il comportamento della pipeline (che salta gli step se trova gli output).

- `frg_03-2019_07-2019/`: copia di `data/results/frg_03-2019_07-2019/` (2201 file). Checksum in `SHA256SUMS_results.txt`; verifica con `sha256sum -c SHA256SUMS_results.txt` da questa cartella.
- `SHA256SUMS_inputs_inplace.txt`: checksum degli input lasciati in `data/` (`pred/`, `trig/`, modello `.h5`, cataloghi). Serve a verificare che nessuno li sovrascriva (docs/WORKING_RULES.md regola 6). Verifica con `sha256sum -c` dalla cartella `data/`.

Stato noto di questi file (vedi `docs/DIFF_UPSTREAM.md` §6): `pred/frg_*` e `pred/bkg_*` erano già stati sovrascritti dallo step 4 (nessun NaN, maschera SAA = 10.0); `trig/` è stato calcolato su quegli input sanificati. **Risultati invalidi** (docs/WORKING_RULES.md §1).
