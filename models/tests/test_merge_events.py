from typing import List, Tuple, Sequence

# Test datasets
dataA = [(1, 4), (5, 9), (10, 11), (12, 13), (20, 24), (25, 26)]
results1 = ((1, 9), (10, 13), (20, 26))
results2 = ((1, 4), (5, 9), (10, 11), (12, 13), (20, 24), (25, 26))
results3 = ((1, 4), (5, 9), (10, 13), (20, 24), (25, 26))
results4 = ((1, 26),)

dataB = [(32, 56), (57, 58), (60, 64), (99, 100)]
results5 = ((32, 56), (57, 64), (99, 100))


def merge(data: Sequence[Tuple[int, int]], length: int = 10) -> List[Tuple[int, int]]:
    """
    Accorpa intervalli temporali contigui o ravvicinati se la distanza
    tra la fine del segmento corrente e l'inizio del blocco è inferiore a 'length'.
    """
    if not data:
        return []

    out: List[Tuple[int, int]] = []
    i = 0
    n = len(data)

    while i < n:
        j = 0
        while (i + j < n) and (data[i + j][1] - data[i][0] < length):
            j += 1

        if j == 0:
            out.append((data[i][0], data[i][1]))
            i += 1
        else:
            out.append((data[i][0], data[i + j - 1][1]))
            i += j

    return out


def run_tests():
    test_cases = [
        ("Test 1 (length=10)", dataA, 10, results1),
        ("Test 2 (length=3)",  dataA, 3,  results2),
        ("Test 3 (length=4)",  dataA, 4,  results3),
        ("Test 4 (length=666)", dataA, 666, results4),
        ("Test 5 (length=10, set B)", dataB, 10, results5),
    ]

    for name, dataset, length, expected in test_cases:
        res = tuple(merge(dataset, length=length))
        assert res == expected, f"{name} FAILED: got {res} instead of {expected}"
        print(f"[{name}] PASSED")


if __name__ == '__main__':
    run_tests()