from math import log, sqrt
from typing import Any, Callable, List, Sequence, Tuple
import numpy as np


class Curve:
    """
    Poisson-FOCuS quadratic curve representation (Kester Ward, 2021).
    Tracks accumulated evidence for an anomalous rate increase.
    """

    def __init__(self, k_t: float, lambda_1: float, t: int = 0) -> None:
        self.a: float = float(k_t)
        self.b: float = -float(lambda_1)
        self.t: int = t

    def __repr__(self) -> str:
        return f"({int(self.a):d}, {self.b:.2f}, {self.t:d})"

    def evaluate(self, mu: float) -> float:
        """Evaluates the log-likelihood ratio at parameter mu."""
        if mu <= 0:
            return 0.0
        return max(self.a * log(mu) + self.b * (mu - 1.0), 0.0)

    def update(self, k_t: float, lambda_1: float) -> "Curve":
        """Updates the curve with an incoming observation (k_t counts, lambda_1 background)."""
        return Curve(self.a + k_t, -self.b + lambda_1, self.t - 1)

    def xmax(self) -> float:
        """Returns the mu parameter value at which the curve achieves its peak."""
        if abs(self.b) < 1e-12:
            return 1.0
        return -self.a / self.b

    def ymax(self) -> float:
        """Returns the peak significance value of the curve."""
        return self.evaluate(self.xmax())

    def is_negative(self) -> bool:
        """Checks if the derivative at mu=1 is non-positive (no evidence for positive change)."""
        return (self.a + self.b) <= 0.0

    def dominates(self, other_curve: "Curve") -> bool:
        """Pruning condition: determines if this curve dominates another over the domain."""
        return (self.a + self.b >= other_curve.a + other_curve.b) and (
            self.a * other_curve.b <= other_curve.a * self.b
        )


def focus_step(
    curve_list: Sequence[Curve], k_t: float, lambda_1: float
) -> Tuple[List[Curve], float, int]:
    """
    Executes a single time-step of the Poisson-FOCuS sequential change-point algorithm:
    updates existing curves, prunes dominated ones, and tracks the global maximum.
    """
    if not curve_list:
        if k_t <= lambda_1:
            return [], 0.0, 0
        updated_c = Curve(k_t, lambda_1, t=-1)
        return [updated_c], updated_c.ymax(), updated_c.t

    updated_c = curve_list[0].update(k_t, lambda_1)
    if updated_c.is_negative():
        return [], 0.0, 0

    new_curve_list: List[Curve] = [updated_c]
    global_max: float = updated_c.ymax()
    time_offset: int = updated_c.t

    for c in list(curve_list[1:]) + [Curve(0.0, 0.0)]:
        candidate_c = c.update(k_t, lambda_1)
        if new_curve_list[-1].dominates(candidate_c):
            break

        new_curve_list.append(candidate_c)
        ymax_val = candidate_c.ymax()
        if ymax_val > global_max:
            global_max = ymax_val
            time_offset = candidate_c.t

    return new_curve_list, global_max, time_offset


def build_focus_runner(
    mu_min: float = 1.0, t_max: int = 0
) -> Callable[[Sequence[float], Sequence[float]], Tuple[List[float], List[Any]]]:
    """
    Configures and returns a Poisson-FOCuS scanning runner.

    :param mu_min: Minimum rate ratio threshold (mu_min >= 1.0) to filter faint transients.
    :param t_max: Maximum lookback horizon (t_max >= 0) to disregard old change-points.
    :return: Executable function (observed_counts, bkg_estimates) -> (significances, offsets).
    """
    assert mu_min >= 1.0, "mu_min must be >= 1.0"
    assert t_max >= 0, "t_max must be >= 0"

    ab_crit = (1.0 - mu_min) / log(mu_min) if mu_min > 1.0 else None
    t_max_cutoff = -t_max

    def run(xs: Sequence[float], bs: Sequence[float]) -> Tuple[List[float], List[Any]]:
        out: List[float] = []
        out_offset: List[Any] = []
        curve_list: List[Curve] = []

        for x_t, lambda_t in zip(xs, bs):
            if not np.isnan(lambda_t):
                # Prune curves exceeding mu_min or lookback t_max thresholds
                if curve_list and (
                    (ab_crit is not None and curve_list[0].a <= ab_crit * curve_list[0].b)
                    or (t_max_cutoff != 0 and curve_list[0].t < t_max_cutoff)
                ):
                    curve_list = curve_list[1:]

                # Execute sequential FOCuS update step
                curve_list, global_max, offset = focus_step(curve_list, x_t, lambda_t)
                out.append(sqrt(2.0 * global_max))
                out_offset.append(offset)
            else:
                # Reset curve states during South Atlantic Anomaly (SAA) passages
                curve_list = []
                out.append(np.nan)
                out_offset.append(np.nan)

        return out, out_offset

    return run


# Backward-compatibility alias to preserve legacy call signatures
set = build_focus_runner