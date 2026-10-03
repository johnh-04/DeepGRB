from typing import Sequence, List, Optional

# 12 rivelatori NaI: n0, n1, ..., n9, na, nb
KDETS: Sequence[str] = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b')
# 3 bande di energia: r0 (molle), r1 (medio), r2 (duro)
KRANGES: Sequence[str] = ('0', '1', '2')


def get_keys(ns: Sequence[str] = KDETS, rs: Sequence[str] = KRANGES) -> List[str]:
    """
    Costruisce la lista completa delle chiavi dei canali dei rivelatori (es. ['n0_r0', 'n0_r1', ..., 'nb_r2']).
    
    :param ns: sequenza di identificatori dei rivelatori (es. '0', '1', ..., 'b')
    :param rs: sequenza di identificatori di bande energetiche (es. '0', '1', '2')
    :return: lista di stringhe con formato 'n<det>_r<range>'
    """
    return [f"n{det}_r{rng}" for det in ns for rng in rs]


def filter_keys(ls: Sequence[str], ns: Sequence[str], rs: Optional[Sequence[str]] = None) -> List[str]:
    """
    Filtra una lista di chiavi mantenendo solo i rivelatori e le bande energetiche richieste.
    
    :param ls: lista o sequenza di chiavi esistenti (es. ['n1_r0', 'n3_r2'])
    :param ns: sequenza di rivelatori da conservare
    :param rs: sequenza di bande energetiche da conservare (default: ('0', '1', '2'))
    :return: lista ordinata di chiavi filtrate
    """
    if rs is None:
        rs = KRANGES

    # Estrazione sicura: supporta stringhe con formato 'n<det>_r<range>'
    index_labels = {k.split('_')[0][1:] for k in ls if '_' in k and k.startswith('n')}
    range_labels = {k.split('_')[1][1:] for k in ls if '_' in k and len(k.split('_')[1]) > 1}

    out_index = index_labels.intersection(set(ns))
    out_range = range_labels.intersection(set(rs))
    
    return sorted(get_keys(sorted(out_index), sorted(out_range)))