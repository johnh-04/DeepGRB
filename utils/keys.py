"""Channel keys of the 12 NaI detectors x 3 energy ranges ('n<det>_r<range>')."""

from typing import List, Sequence

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
