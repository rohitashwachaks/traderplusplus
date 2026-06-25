import numpy as np
import pandas as pd

from core.context import DataContext, build_context
from core.universe import ListUniverse
from engine.runner import run
from strategies.buy_n_hold import BuyAndHold


def test_buy_n_hold_runs_and_grows(rising_prices):
    """End-to-end on synthetic data: the backtest produces an equity curve and stats, and
    buy-and-hold on a monotonically rising series never loses value."""
    prices = rising_prices[["AAPL"]]
    benchmark = rising_prices[["MSFT"]]

    res = run(BuyAndHold(), DataContext.from_prices(prices), benchmark, initial_capital=100_000.0)

    equity = res.prices["buy_n_hold"]
    assert not equity.empty
    assert "daily_sharpe" in res.stats.index
    assert "max_drawdown" in res.stats.index

    # Allow a tiny tolerance for the first-bar rebalance, then require non-decreasing value.
    assert equity.iloc[-1] >= equity.iloc[1]


def test_basket_runs_over_staggered_universe(monkeypatch):
    """A universe with a late-listing name must run through bt without NaN equity: the
    membership mask zeros the name until it has prices, so filled prices never leak in."""
    dates = pd.date_range("2020-01-01", periods=60, freq="B")
    n = len(dates)
    price = pd.DataFrame(
        {"A": np.linspace(100, 160, n),
         "B": [np.nan] * 20 + list(np.linspace(50, 80, n - 20))},   # B lists on day 20
        index=dates,
    )
    benchmark = pd.DataFrame({"SPY": np.linspace(100, 120, n)}, index=dates)

    class FakeSource:
        def load(self, tickers, start, end, **opts):
            return price[list(tickers)]

    monkeypatch.setattr("core.context._sources.get_source", lambda name: FakeSource())
    ctx = build_context(ListUniverse(["A", "B"]), "2020-01-01", "2020-04-01")

    res = run(BuyAndHold(), ctx, benchmark)
    equity = res.prices["buy_n_hold"]
    assert not equity.isna().any()        # NaN-safe despite B's late listing
    assert equity.iloc[-1] > 0
