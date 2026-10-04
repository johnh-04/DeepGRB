"""Channel keys of the 12 NaI detectors x 3 energy ranges ('n<det>_r<range>')."""

from typing import Sequence, List, Optional

# 12 NaI detectors: n0, n1, ..., n9, na, nb
KDETS: Sequence[str] = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b')
# 3 energy ranges: r0 (soft), r1 (medium), r2 (hard)
KRANGES: Sequence[str] = ('0', '1', '2')


def get_keys(ns: Sequence[str] = KDETS, rs: Sequence[str] = KRANGES) -> List[str]:
    """
    All channel keys of the given detectors and ranges (e.g. ['n0_r0', 'n0_r1', ..., 'nb_r2']).

    :param ns: detector identifiers ('0', '1', ..., 'b')
    :param rs: energy range identifiers ('0', '1', '2')
    :return: keys formatted 'n<det>_r<range>'
    """
    return [f"n{det}_r{rng}" for det in ns for rng in rs]


def filter_keys(ls: Sequence[str], ns: Sequence[str], rs: Optional[Sequence[str]] = None) -> List[str]:
    """
    Keeps the keys of the requested detectors and energy ranges.

    :param ls: existing keys (e.g. ['n1_r0', 'n3_r2'])
    :param ns: detectors to keep
    :param rs: energy ranges to keep (default: ('0', '1', '2'))
    :return: sorted filtered keys
    """
    if rs is None:
        rs = KRANGES

    # keys formatted 'n<det>_r<range>' only
    index_labels = {k.split('_')[0][1:] for k in ls if '_' in k and k.startswith('n')}
    range_labels = {k.split('_')[1][1:] for k in ls if '_' in k and len(k.split('_')[1]) > 1}

    out_index = index_labels.intersection(set(ns))
    out_range = range_labels.intersection(set(rs))
    
    return sorted(get_keys(sorted(out_index), sorted(out_range)))