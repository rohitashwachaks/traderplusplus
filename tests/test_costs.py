"""Trading costs: nonzero cost_bps must strictly reduce net returns for a trading strategy."""
from core.context import DataContext
from engine.runner import run
from strategies.momentum import Momentum


def test_costs_reduce_final_equity(choppy_prices):
    prices = choppy_prices
    benchmark = choppy_prices.rename(columns={"AAPL": "SPY"})
    strategy = Momentum(short_window=5, long_window=15)

    frictionless = run(strategy, DataContext.from_prices(prices), benchmark)
    costly = run(strategy, DataContext.from_prices(prices), benchmark, cost_bps=50.0)

    # The oscillating series makes momentum trade repeatedly, so 50 bps per side must bite.
    assert costly.prices["momentum"].iloc[-1] < frictionless.prices["momentum"].iloc[-1]


def test_zero_cost_is_the_default_and_identical(choppy_prices):
    prices = choppy_prices
    benchmark = choppy_prices.rename(columns={"AAPL": "SPY"})
    strategy = Momentum(short_window=5, long_window=15)

    default = run(strategy, DataContext.from_prices(prices), benchmark)
    explicit_zero = run(strategy, DataContext.from_prices(prices), benchmark, cost_bps=0.0)

    assert default.prices["momentum"].equals(explicit_zero.prices["momentum"])
