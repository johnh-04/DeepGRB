from collections import deque
from functools import reduce
from math import log, sqrt
from typing import Callable, List, Optional, Sequence, Tuple


def sign(n: float, b: float) -> float:
    """Computes the Poisson log-likelihood ratio for observed n vs background b."""
    if n > b and b > 0:
        return n * log(n / b) - (n - b)
    return 0.0


def nmin(a: Optional[float], b: Optional[float]) -> float:
    """Helper minimum function treating None as infinity."""
    val_a = float("inf") if a is None else a
    val_b = float("inf") if b is None else b
    return min(val_a, val_b)


def build_paramtrig_runner(
    threshold: float,
    bg_len: int,
    fg_len: int,
    hs: Sequence[int],
    gs: Sequence[int]
) -> Callable[[Sequence[float]], Tuple[float, int, int]]:
    """
    Builds a sliding-window parametric trigger runner replicating onboard GBM logic.

    :param threshold: Significance trigger threshold.
    :param bg_len: Length of background estimation window.
    :param fg_len: Length of foreground observation window.
    :param hs: Window step lengths.
    :param gs: Window offset phases.
    :return: Function that scans input count series and returns (significance, start_time, trigger_time).
    """
    assert len(hs) == len(gs), "hs and gs must have identical length"
    assert reduce(lambda x, y: x and y, [g < h for h, g in zip(hs, gs)]), "All offsets g must be strictly less than h"

    buflen = fg_len + bg_len
    allchecks = list(zip(hs, gs))
    scaled_threshold = (threshold ** 2) / 2.0

    def run(x: Sequence[float]) -> Tuple[float, int, int]:
        # Using deque for O(1) sliding window eviction instead of O(N) list.pop(0)
        obsbuf: deque = deque()
        bkg_rate: float = 0.0
        final_t: int = 0

        for t_idx, x_t in enumerate(x):
            final_t = t_idx
            global_max: float = 0.0
            time_offset: int = 0
            obsbuf.append(x_t)

            if t_idx >= buflen:
                bkg_rate += obsbuf[bg_len] / bg_len
                bkg_rate -= obsbuf.popleft() / bg_len
                schedule = allchecks
            elif t_idx >= bg_len:
                schedule = [(h, g) for (h, g) in allchecks if h <= t_idx - bg_len + 1]
            else:
                bkg_rate += obsbuf[-1] / bg_len
                schedule = []

            # Check scheduled time window scales
            buf_len_current = len(obsbuf)
            for h, g in schedule:
                if (t_idx + 1) % h == g and buf_len_current >= h:
                    recent_sum = sum(obsbuf[buf_len_current - i - 1] for i in range(h))
                    s_stat = sign(recent_sum, bkg_rate * h)
                    if s_stat > global_max:
                        global_max = s_stat
                        time_offset = -h

            if global_max > scaled_threshold:
                return sqrt(2.0 * global_max), t_idx + time_offset + 1, t_idx

        # Return null trigger tuple if no change exceeded threshold by end of series
        return 0.0, final_t + 1, final_t

    return run


# Backward-compatibility alias
set = build_paramtrig_runner

# Standard operational configuration for Fermi GBM sliding-window triggers
set_gbm = lambda threshold: build_paramtrig_runner(
    threshold=threshold,
    bg_len=1062,
    fg_len=250,
    hs=[1, 2, 2, 4, 4, 8, 8, 16, 16, 32, 32, 64, 64, 128, 128, 256, 256],
    gs=[0, 0, 1, 0, 2, 0, 4, 0, 8, 0, 16, 0, 32, 0, 64, 0, 128],
)