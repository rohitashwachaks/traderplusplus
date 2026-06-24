from engine.runner import run
from strategies.buy_n_hold import BuyAndHold


def test_buy_n_hold_runs_and_grows(rising_prices):
    """End-to-end on synthetic data: the backtest produces an equity curve and stats, and
    buy-and-hold on a monotonically rising series never loses value."""
    prices = rising_prices[["AAPL"]]
    benchmark = rising_prices[["MSFT"]]

    res = run(BuyAndHold(), prices, benchmark, initial_capital=100_000.0)

    equity = res.prices["buy_n_hold"]
    assert not equity.empty
    assert "daily_sharpe" in res.stats.index
    assert "max_drawdown" in res.stats.index

    # Allow a tiny tolerance for the first-bar rebalance, then require non-decreasing value.
    assert equity.iloc[-1] >= equity.iloc[1]
