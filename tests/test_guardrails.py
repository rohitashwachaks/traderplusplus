import numpy as np
import pandas as pd

from core.context import DataContext
from guardrails.stop_loss import StopLoss
from strategies.buy_n_hold import BuyAndHold
from strategies.momentum import Momentum


def _panel(values):
    dates = pd.date_range("2022-01-01", periods=len(values), freq="B")
    return pd.DataFrame({"AAPL": values}, index=dates)


def _w(strat, prices):
    """Strategy weights from a price-only context — keeps these guardrail tests terse."""
    return strat.weights(DataContext.from_prices(prices))


# Rise from 100 to a peak of 110, fall back, then sit flat — a clean drawdown to test on.
_RISE_FALL = _panel([100, 102, 104, 106, 108, 110, 108, 106, 104] + [100] * 11)


def test_stop_loss_no_lookahead(choppy_prices):
    """The guardrail must stay no-look-ahead: truncating future bars can't change a past
    adjusted weight."""
    strat, guard = Momentum(3, 10), StopLoss(0.05, trailing=True)
    full = guard.apply(choppy_prices, _w(strat, choppy_prices))
    for i in (40, 60, 80, 100):
        t = choppy_prices.index[i]
        sub = choppy_prices.loc[:t]
        trunc = guard.apply(sub, _w(strat, sub))
        assert (full.loc[t] == trunc.loc[t]).all(), f"look-ahead at {t}"


def test_trailing_stop_exits_and_latches():
    """A 5% trailing stop exits the bar after price falls 5% from its peak, then stays
    out (buy-and-hold keeps wanting in, but the stop is latched)."""
    weights = _w(BuyAndHold(), _RISE_FALL)
    adjusted = StopLoss(0.05, trailing=True).apply(_RISE_FALL, weights)["AAPL"]

    assert adjusted.iloc[3] == 1.0           # still fully invested during the run-up
    assert adjusted.iloc[-1] == 0.0          # stopped out by the end
    # Once it goes flat it never re-enters (no thrashing).
    first_zero = np.argmax(adjusted.to_numpy() == 0.0)
    assert (adjusted.iloc[first_zero:] == 0.0).all()


def test_stop_pct_is_configurable():
    """A wider 20% stop never triggers on this ~9% drawdown."""
    weights = _w(BuyAndHold(), _RISE_FALL)
    adjusted = StopLoss(0.20, trailing=True).apply(_RISE_FALL, weights)["AAPL"]
    assert (adjusted == 1.0).all()


def test_trailing_vs_fixed():
    """Falling to 104 from a peak of 110 (entry 100): trailing stops (−5% from peak),
    fixed does not (still well above the entry price)."""
    prices = _panel([100, 102, 104, 106, 108, 110, 108, 106, 104] + [104] * 6)
    weights = _w(BuyAndHold(), prices)
    trailing = StopLoss(0.05, trailing=True).apply(prices, weights)["AAPL"]
    fixed = StopLoss(0.05, trailing=False).apply(prices, weights)["AAPL"]
    assert trailing.iloc[-1] == 0.0
    assert fixed.iloc[-1] == 1.0


def test_invalid_pct_raises():
    for bad in (0.0, 1.0, -0.1, 5):
        try:
            StopLoss(pct=bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for pct={bad}")
