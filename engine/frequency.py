import bt
import numpy as np
import pandas as pd

# Canonical frequencies and their accepted aliases.
_CANON = {
    "D": ("d", "1d", "day", "daily"),
    "W": ("w", "1w", "week", "weekly"),
    "M": ("m", "1m", "month", "monthly"),
    "Q": ("q", "quarter", "quarterly"),
    "Y": ("y", "a", "year", "yearly", "annual", "annually"),
}
_ALIAS = {alias: canon for canon, aliases in _CANON.items() for alias in aliases}

_RUN = {
    "D": bt.algos.RunDaily,
    "W": bt.algos.RunWeekly,
    "M": bt.algos.RunMonthly,
    "Q": bt.algos.RunQuarterly,
    "Y": bt.algos.RunYearly,
}


def normalize(freq: str) -> str:
    """Map a frequency string to its canonical form (one of D, W, M, Q, Y)."""
    key = str(freq).strip().lower()
    if key not in _ALIAS:
        raise ValueError(f"Unknown frequency '{freq}'. Use D, W, M, Q or Y "
                         "(or daily/weekly/monthly/quarterly/yearly).")
    return _ALIAS[key]


def run_algo(freq: str) -> bt.Algo:
    """The ``bt`` Run algo that fires on the given rebalance frequency."""
    return _RUN[normalize(freq)]()


class RunOnDays(bt.Algo):
    """Fire on an explicit set of dates — the engine's seam for guardrail exits, which must
    trade the day they happen rather than wait for the scheduled rebalance."""

    def __init__(self, days: pd.DatetimeIndex):
        super().__init__()
        self._days = set(pd.DatetimeIndex(days))

    def __call__(self, target) -> bool:
        return target.now in self._days


class AnyOf(bt.Algo):
    """True if any child algo fires. Every child is evaluated (no short-circuit), so
    stateful Run algos keep their internal date tracking consistent."""

    def __init__(self, algos: list[bt.Algo]):
        super().__init__()
        self._algos = algos

    def __call__(self, target) -> bool:
        results = [algo(target) for algo in self._algos]
        return any(results)


def resample_reconstitution(weights: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Refresh target weights only on each period boundary, holding them constant in
    between — i.e. reconstitute the selection/weights every `freq` and let `bt` rebalance
    back to that frozen target between boundaries.

    Daily means no change (recompute every day). Coarser frequencies sample the weights on
    the first trading day of each period and forward fill. Forward fill only ever uses past
    boundaries, so this stays no-look-ahead.
    """
    canon = normalize(freq)
    if canon == "D":
        return weights

    period = weights.index.to_period(canon).to_numpy()
    boundary = np.empty(len(period), dtype=bool)
    boundary[0] = True
    boundary[1:] = period[1:] != period[:-1]

    sampled = weights.copy()
    sampled.loc[~boundary] = np.nan
    return sampled.ffill()
