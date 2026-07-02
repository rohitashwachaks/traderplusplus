import numpy as np
import pandas as pd

from core.context import DataContext
from strategies.cross_sectional_momentum import CrossSectionalMomentum


def _panel():
    dates = pd.date_range("2022-01-01", periods=80, freq="B")
    t = np.arange(80)
    return pd.DataFrame({
        "WIN": 100 * (1.010 ** t),   # fastest riser
        "MID": 100 * (1.004 ** t),
        "LOSE": 100 * (0.998 ** t),  # declining
    }, index=dates)


def _w(strat, prices):
    return strat.weights(DataContext.from_prices(prices))


def test_selects_top_by_momentum():
    weights = _w(CrossSectionalMomentum(lookback=20, top_n=1), _panel()).iloc[-1]
    assert weights["WIN"] == 1.0
    assert weights["MID"] == 0.0 and weights["LOSE"] == 0.0


def test_top_n_holds_equal_weight_and_sums_to_one():
    weights = _w(CrossSectionalMomentum(lookback=20, top_n=2), _panel()).iloc[-1]
    assert weights.sum() == 1.0
    held = weights[weights > 0]
    assert len(held) == 2 and held.nunique() == 1   # equal weight among the two held


def test_default_top_n_is_half_the_basket():
    # 3 tickers -> top half = 1
    weights = _w(CrossSectionalMomentum(lookback=20, top_n=None), _panel()).iloc[-1]
    assert (weights > 0).sum() == 1


def test_no_lookahead():
    strat, prices = CrossSectionalMomentum(lookback=20, top_n=2), _panel()
    full = _w(strat, prices)
    t = prices.index[60]
    trunc = _w(strat, prices.loc[:t])
    assert (full.loc[t] == trunc.loc[t]).all()


def test_defaults_to_monthly():
    strat = CrossSectionalMomentum()
    assert strat.rebalance_freq == "M" and strat.reconstitution_freq == "M"
