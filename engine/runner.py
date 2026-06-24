from typing import Sequence

import bt
import pandas as pd

from engine import frequency
from guardrails.base import Guardrail
from strategies.base import TargetWeightStrategy


def target_weights(
    strategy: TargetWeightStrategy,
    prices: pd.DataFrame,
    guardrails: Sequence[Guardrail] | None = None,
) -> pd.DataFrame:
    """The strategy's target weights after guardrails and reconstitution sampling.

    Shared by the backtest and the paper-trading rebalancer so both compute the target the
    same way. Not yet reindexed/forward-filled onto the trading calendar — callers decide.
    """
    weights = strategy.weights(prices)
    for guardrail in guardrails or ():
        weights = guardrail.apply(prices, weights)
    return frequency.resample_reconstitution(weights, strategy.reconstitution_freq)


def run(
    strategy: TargetWeightStrategy,
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    initial_capital: float = 100_000.0,
    guardrails: Sequence[Guardrail] | None = None,
) -> bt.backtest.Result:
    """Backtest ``strategy`` against a buy-and-hold benchmark on ``bt``.

    The strategy's target weights are passed through any ``guardrails`` (risk overlays,
    e.g. a stop-loss), then reindexed onto the trading calendar and forward filled, so the
    portfolio rebalances toward the latest target each day and sits idle when the target is
    unchanged. The benchmark is a one-off full allocation to its ticker.

    Args:
        strategy: produces target weights from the price panel.
        prices: dates x tickers panel the strategy trades.
        benchmark_prices: single-column panel for the benchmark ticker.
        initial_capital: starting capital for both backtests.
        guardrails: risk overlays applied to the strategy's weights, in order.

    Returns:
        The combined ``bt`` result holding both the strategy and benchmark.
    """
    weights = target_weights(strategy, prices, guardrails)
    weights = weights.reindex(prices.index).ffill().fillna(0.0)

    strat = bt.Strategy(
        strategy.name,
        [frequency.run_algo(strategy.rebalance_freq), bt.algos.SelectAll(),
         bt.algos.WeighTarget(weights), bt.algos.Rebalance()],
    )
    strat_test = bt.Backtest(strat, prices, name=strategy.name, initial_capital=initial_capital)

    bench_name = benchmark_prices.columns[0]
    bench = bt.Strategy(
        bench_name,
        [bt.algos.RunOnce(), bt.algos.SelectAll(), bt.algos.WeighEqually(), bt.algos.Rebalance()],
    )
    bench_test = bt.Backtest(bench, benchmark_prices, name=bench_name, initial_capital=initial_capital)

    return bt.run(strat_test, bench_test)
