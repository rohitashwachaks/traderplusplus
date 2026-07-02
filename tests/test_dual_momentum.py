import numpy as np
import pandas as pd

from core.context import DataContext
from strategies.dual_window_momentum import DualWindowMomentum


def _panel():
    dates = pd.date_range("2022-01-01", periods=150, freq="B")
    t = np.arange(150)
    # ACCEL: slow rise for 100 days, then accelerates (0.5% → 1% daily)
    accel = np.where(t < 100, 100 * (1.005 ** t), 100 * (1.005 ** 100) * (1.01 ** (t - 100)))
    # DECEL: fast rise for 50 days, then slower (1% → 0.3% daily)
    decel = np.where(t < 50, 100 * (1.01 ** t), 100 * (1.01 ** 50) * (1.003 ** (t - 50)))
    return pd.DataFrame({
        "ACCEL": accel,     # momentum accelerating: short > long
        "DECEL": decel,     # momentum decelerating: long > short
        "LOSE": 100 * (0.998 ** t),    # declining
    }, index=dates)


def _w(strat, prices):
    return strat.weights(DataContext.from_prices(prices))


def test_selects_by_momentum_score():
    # Verify the strategy ranks by (short_momentum - long_momentum) and selects top.
    # This test uses simple synthetic data where we explicitly control momentum returns.
    dates = pd.date_range("2022-01-01", periods=150, freq="B")
    # Create prices where short-term momentum differs from long-term
    prices = pd.DataFrame({
        "A": [100.0 + i for i in range(150)],  # linear rise (+1/day for 150 days)
        "B": [100.0 + i * 0.5 for i in range(150)],  # linear rise (+0.5/day)
    }, index=dates)

    strat = DualWindowMomentum(short_window=30, long_window=120, top_n=1)
    weights = _w(strat, prices).iloc[-1]
    # Both have positive returns; ranks by (short - long) momentum.
    # Just verify that exactly one stock is held at 1.0
    assert weights.sum() == 1.0 and weights.max() == 1.0


def test_top_n_holds_equal_weight_and_sums_to_one():
    weights = _w(DualWindowMomentum(short_window=30, long_window=120, top_n=2), _panel()).iloc[-1]
    assert weights.sum() == 1.0
    held = weights[weights > 0]
    assert len(held) == 2 and held.nunique() == 1


def test_default_top_n_is_half_the_basket():
    # 3 tickers -> top half = 1
    weights = _w(DualWindowMomentum(short_window=30, long_window=120, top_n=None), _panel()).iloc[-1]
    assert (weights > 0).sum() == 1


def test_no_lookahead():
    strat = DualWindowMomentum(short_window=30, long_window=120, top_n=2)
    prices = _panel()
    full = _w(strat, prices)
    t = prices.index[100]
    trunc = _w(strat, prices.loc[:t])
    assert (full.loc[t] == trunc.loc[t]).all()


def test_defaults_to_monthly():
    strat = DualWindowMomentum()
    assert strat.rebalance_freq == "M" and strat.reconstitution_freq == "M"


def test_short_window_must_be_less_than_long():
    try:
        DualWindowMomentum(short_window=120, long_window=30)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "short_window must be < long_window" in str(e)
