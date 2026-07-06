from typing import Sequence

import bt
import pandas as pd

from core.context import DataContext
from engine import frequency
from guardrails.base import Guardrail
from strategies.base import TargetWeightStrategy


def _guardrail_panels(guardrail: Guardrail, ctx: DataContext) -> dict[str, pd.DataFrame]:
    """The extra panels a guardrail declares, where the context actually has them."""
    return {name: ctx.panel(name) for name in guardrail.requires if ctx.has(name)}


def target_weights(
    strategy: TargetWeightStrategy,
    ctx: DataContext,
    guardrails: Sequence[Guardrail] | None = None,
) -> pd.DataFrame:
    """The strategy's target weights: reconstitution sampling first, then guardrails.

    Shared by the backtest and the paper-trading rebalancer so both compute the target the
    same way. **Order matters and is a correctness guarantee**: guardrails overlay the
    *reconstituted* target at daily resolution, so a mid-period stop-out is never erased by
    the period resample (it used to be — the exit silently slid to the next boundary).
    A strategy's own ``guardrails`` (class/instance attribute) apply first, then any passed
    here; each receives ``ctx.price`` plus whatever ``requires`` panels the context holds
    (e.g. ``high``/``low``).
    """
    weights = frequency.resample_reconstitution(strategy.weights(ctx), strategy.reconstitution_freq)
    for guardrail in (*strategy.guardrails, *(guardrails or ())):
        weights = guardrail.apply(ctx.price, weights, **_guardrail_panels(guardrail, ctx))
    return weights


def run(
    strategy: TargetWeightStrategy,
    ctx: DataContext,
    benchmark_prices: pd.DataFrame,
    initial_capital: float = 100_000.0,
    guardrails: Sequence[Guardrail] | None = None,
    cost_bps: float = 0.0,
) -> bt.backtest.Result:
    """Backtest ``strategy`` against a buy-and-hold benchmark on ``bt``.

    The strategy's weights are reconstitution-sampled onto the trading calendar, then passed
    through any ``guardrails`` (risk overlays, e.g. a stop-loss). Trades fire on the
    strategy's rebalance schedule **plus** every day a guardrail changes the target — a
    stop-out executes at that day's close no matter how coarse the rebalance frequency.
    The benchmark is a one-off full allocation to its ticker.

    Args:
        strategy: produces target weights from the data context.
        ctx: the data context the strategy trades (``ctx.price`` is the panel ``bt`` uses).
        benchmark_prices: single-column panel for the benchmark ticker.
        initial_capital: starting capital for both backtests.
        guardrails: risk overlays applied to the strategy's weights, in order.
        cost_bps: commission + slippage charged per trade, in basis points of traded
            notional (both sides, strategy and benchmark alike). ``0`` = frictionless —
            the caller must stamp that on the report. Short borrow is never modeled here.

    Returns:
        The combined ``bt`` result holding both the strategy and benchmark.
    """
    prices = ctx.price
    scheduled = frequency.resample_reconstitution(strategy.weights(ctx), strategy.reconstitution_freq)
    scheduled = scheduled.reindex(prices.index).ffill().fillna(0.0)
    weights = scheduled
    for guardrail in (*strategy.guardrails, *(guardrails or ())):
        weights = guardrail.apply(prices, weights, **_guardrail_panels(guardrail, ctx))
    weights = weights.fillna(0.0)

    # Risk exits trade the day they happen: besides the scheduled rebalance, fire on every
    # day a guardrail's effect on the target changes. Strategy-driven changes still wait for
    # the schedule — exits are risk decisions, entries are strategy decisions.
    effect = (scheduled - weights).fillna(0.0)
    exit_days = prices.index[effect.ne(effect.shift(1).fillna(0.0)).any(axis=1)]
    run_trigger = frequency.run_algo(strategy.rebalance_freq)
    if len(exit_days):
        run_trigger = frequency.AnyOf([run_trigger, frequency.RunOnDays(exit_days)])

    # bt needs a NaN-free panel. Names not yet listed / delisted carry a 0 weight (the context's
    # membership mask is price.notna()), so forward/back-filling their prices never affects NAV.
    bt_prices = prices.ffill().bfill()

    commissions = None
    if cost_bps:
        def commissions(quantity: float, price: float) -> float:
            return abs(quantity) * price * cost_bps / 1e4

    strat = bt.Strategy(
        strategy.name,
        [run_trigger, bt.algos.SelectAll(),
         bt.algos.WeighTarget(weights), bt.algos.Rebalance()],
    )
    strat_test = bt.Backtest(strat, bt_prices, name=strategy.name,
                             initial_capital=initial_capital, commissions=commissions)

    bench_name = benchmark_prices.columns[0]
    bench = bt.Strategy(
        bench_name,
        [bt.algos.RunOnce(), bt.algos.SelectAll(), bt.algos.WeighEqually(), bt.algos.Rebalance()],
    )
    bench_test = bt.Backtest(bench, benchmark_prices, name=bench_name,
                             initial_capital=initial_capital, commissions=commissions)

    return bt.run(strat_test, bench_test)
