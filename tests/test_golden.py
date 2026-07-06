"""Golden-file reproducibility: a pinned backtest whose equity curve must never drift.

Any refactor — or dependency bump — that changes these numbers is changing *results*, and
must either be a deliberate, explained decision (update the values in the same commit, with
the reason) or a bug. Failing here is the mechanism behind non-negotiable #4.
"""
import numpy as np
import pandas as pd
import pytest

from core.context import DataContext
from engine.runner import run
from strategies.cross_sectional_momentum import CrossSectionalMomentum

GOLDEN = {0: 100.0, 50: 100.72192126336591, 100: 94.95467449787837,
          150: 78.32418437904425, 199: 76.40165060430316}


def test_pinned_backtest_reproduces_exactly():
    dates = pd.date_range("2021-01-04", periods=200, freq="B")
    t = np.arange(200, dtype=float)
    prices = pd.DataFrame({
        "AAA": 100 * 1.0008 ** t,
        "BBB": 80 + 10 * np.sin(t / 9.0),
        "CCC": 120 * 0.9997 ** t,
    }, index=dates)
    benchmark = pd.DataFrame({"BENCH": 100 + 0.05 * t}, index=dates)

    res = run(CrossSectionalMomentum(lookback=20, top_n=1),
              DataContext.from_prices(prices), benchmark)
    equity = res.prices["xs_momentum"]

    for i, expected in GOLDEN.items():
        assert float(equity.iloc[i]) == pytest.approx(expected, rel=1e-9), (
            f"equity[{i}] drifted from the golden value — results changed"
        )
