import numpy as np
import pandas as pd
from itertools import groupby
from operator import itemgetter
from typing import List, Tuple, Sequence

from utils.keys import get_keys

DET_NAMES = [
    'n0_r0', 'n0_r1',
    'n1_r0', 'n1_r1',
    'n2_r0', 'n2_r1',
]


def fetch_triggers(
    table: pd.DataFrame,
    threshold: float,
    min_dets_num: int = 2,
    max_dets_num: int = 3,
    active_dets: Sequence[str] = ('0', '1', '2')
) -> List[Tuple[int, int]]:
    """
    Estrae segmenti temporali (start, end) in cui un numero di rivelatori compreso
    tra min_dets_num e max_dets_num supera la soglia di significatività specificata.
    """
    out = {}
    for det in active_dets:
        keys = get_keys(ns=[det], rs=['0', '1'])
        sub_table = table[keys]
        out[det] = (sub_table > threshold).any(axis=1)

    merged_ranges_df = pd.DataFrame(out, index=table.index)
    dets_over_trig = merged_ranges_df.sum(axis=1)
    qualifying_points = dets_over_trig[dets_over_trig >= min_dets_num]

    trig_segs: List[Tuple[int, int]] = []
    for _, group in groupby(enumerate(qualifying_points.index), lambda ix: ix[0] - ix[1]):
        indices = list(map(itemgetter(1), group))
        start, end = indices[0], indices[-1] + 1
        
        # Condizione di veto su un numero eccessivo di rivelatori accesi contemporaneamente
        if (dets_over_trig.loc[start:end] < max_dets_num).all():
            trig_segs.append((start, end))

    return trig_segs


# --- Test fixtures ---
testdataA = np.array([
    [0.0, 1.0, 0.0, 1.0, 0.0, 0.0],
    [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [5.1, 0.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [5.1, 5.1, 0.0, 0.0, 0.0, 0.0],
    [5.1, 5.1, 0.0, 0.0, 0.0, 0.0],
    [5.1, 3.2, 5.1, 0.0, 0.0, 0.0],
    [5.1, 3.2, 5.1, 0.0, 0.0, 0.0],
    [5.1, 0.0, 5.1, 0.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    [5.1, 5.1, 5.1, 5.1, 5.1, 5.1],
])

testdataB = np.full((11, 6), 0.0)
testdataB[:, :2] = 5.1

testdataC = testdataB.copy()
testdataC[0, :2] = np.nan

testdataD = testdataB.copy()
testdataD[4, :] = np.nan


def run_tests():
    cases = [
        ("Case 1", testdataA, {"threshold": 5}, ((6, 9),)),
        ("Case 2", testdataA, {"threshold": 3}, ((6, 9),)),
        ("Case 3", testdataA, {"threshold": 3, "min_dets_num": 1, "max_dets_num": 4}, ((2, 3), (4, 9), (10, 11))),
        ("Case 4", testdataB, {"threshold": 5, "min_dets_num": 2, "max_dets_num": 3}, ()),
        ("Case 5", testdataB, {"threshold": 5, "min_dets_num": 1}, ((0, 11),)),
        ("Case 6", testdataC, {"threshold": 5, "min_dets_num": 1}, ((1, 11),)),
        ("Case 7", testdataC, {"threshold": 5, "min_dets_num": 2}, ()),
        ("Case 8", testdataD, {"threshold": 5, "min_dets_num": 1}, ((0, 4), (5, 11))),
    ]

    for label, raw_arr, params, expected in cases:
        df = pd.DataFrame(raw_arr, columns=DET_NAMES)
        res = tuple(fetch_triggers(df, **params))
        assert res == expected, f"{label} FAILED: got {res} instead of {expected}"
        print(f"[{label}] PASSED")


if __name__ == '__main__':
    run_tests()