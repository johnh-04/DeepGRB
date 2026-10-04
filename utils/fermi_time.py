"""UTC <-> Fermi MET conversion with astropy only (MET = SI seconds since 2001-01-01 00:00:00 UTC, leap seconds included)."""

from typing import Sequence

import numpy as np
import pandas as pd
from astropy.time import Time, TimeDelta

_EPOCH = Time("2001-01-01T00:00:00", scale="utc")


def utc_to_met(utc: Sequence) -> np.ndarray:
    """UTC strings/timestamps -> MET seconds; missing values give NaN."""
    s = pd.to_datetime(pd.Series(utc), errors="coerce")
    out = np.full(len(s), np.nan)
    ok = s.notna().to_numpy()
    if ok.any():
        t = Time(s[ok].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").tolist(), format="isot", scale="utc")
        out[ok] = (t - _EPOCH).sec
    return out


def met_to_utc(met: Sequence[float]) -> pd.Series:
    """MET seconds -> UTC timestamps."""
    met = np.asarray(met, dtype=float)
    return pd.Series((_EPOCH + TimeDelta(met / 86400.0, format="jd")).to_datetime())
