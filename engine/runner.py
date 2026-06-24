import bt
import pandas as pd

from strategies.base import TargetWeightStrategy


def run(
    strategy: TargetWeightStrategy,
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    initial_capital: float = 100_000.0,
) -> bt.backtest.Result:
    """Backtest ``strategy`` against a buy-and-hold benchmark on ``bt``.

    The strategy's target weights are reindexed onto the trading calendar and forward
    filled, so the portfolio rebalances toward the latest target each day and sits idle
    when the target is unchanged. The benchmark is a one-off full allocation to its ticker.

    Args:
        strategy: produces target weights from the price panel.
        prices: dates x tickers panel the strategy trades.
        benchmark_prices: single-column panel for the benchmark ticker.
        initial_capital: starting capital for both backtests.

    Returns:
        The combined ``bt`` result holding both the strategy and benchmark.
    """
    weights = strategy.weights(prices).reindex(prices.index).ffill().fillna(0.0)

    strat = bt.Strategy(
        strategy.name,
        [bt.algos.RunDaily(), bt.algos.SelectAll(), bt.algos.WeighTarget(weights), bt.algos.Rebalance()],
    )
    strat_test = bt.Backtest(strat, prices, name=strategy.name, initial_capital=initial_capital)

    bench_name = benchmark_prices.columns[0]
    bench = bt.Strategy(
        bench_name,
        [bt.algos.RunOnce(), bt.algos.SelectAll(), bt.algos.WeighEqually(), bt.algos.Rebalance()],
    )
    bench_test = bt.Backtest(bench, benchmark_prices, name=bench_name, initial_capital=initial_capital)

    return bt.run(strat_test, bench_test)
