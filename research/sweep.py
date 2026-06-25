"""Sweep a single-asset strategy across a universe — one independent backtest per name.

Running momentum on one hand-picked ticker is a cherry-pick (selection bias). Running it on
*every* name in a universe and looking at the **distribution** of alpha/beta tells you whether
the rule is a real edge or noise. That distribution is the honest unit of evidence.
"""
import logging
from typing import Callable, Sequence

import pandas as pd

from core.context import DataContext
from core.sources import get_source
from core.universe import Universe
from engine import runner
from guardrails.base import Guardrail
from strategies.base import TargetWeightStrategy

log = logging.getLogger("traderplusplus")


def sweep_universe(
    strategy: TargetWeightStrategy,
    universe: Universe,
    benchmark_prices: pd.DataFrame,
    start: str,
    end: str,
    *,
    source: str = "yahoo",
    interval: str = "1d",
    guardrails: Sequence[Guardrail] | None = None,
    min_days: int = 60,
    price_loader: Callable[[str], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Backtest ``strategy`` independently on every name in ``universe`` vs the benchmark.

    Each name is its own single-asset run; per-name alpha/beta/Sharpe/returns come from
    ``quantstats`` (never hand-rolled). Names with too little or flat history are skipped with
    a logged, narrow condition — not silently swallowed.

    Args:
        strategy: a ``single_asset`` strategy (raises otherwise).
        universe: provides the tickers to sweep.
        benchmark_prices: single-column price panel for the benchmark.
        start, end: date window.
        source, interval: data options for the default price loader.
        guardrails: optional risk overlays applied per name.
        min_days: skip names with fewer than this many return observations.
        price_loader: override how a ticker's price panel is fetched (for tests).

    Returns:
        A per-ticker metrics frame (alpha, beta, sharpe, total_return, benchmark_return,
        excess_return), sorted by alpha descending.
    """
    if not strategy.single_asset:
        raise ValueError(
            f"sweep_universe is for single-asset strategies; '{strategy.name}' pools a basket — "
            f"backtest it directly with engine.runner.run instead."
        )

    import quantstats as qs

    if price_loader is None:
        src = get_source("price")

        def price_loader(ticker: str) -> pd.DataFrame:
            return src.load([ticker], start, end, source=source, interval=interval)

    bench_name = benchmark_prices.columns[0]
    rows: dict[str, dict[str, float]] = {}
    for ticker in universe.tickers():
        try:
            panel = price_loader(ticker)
        except ValueError as exc:  # to_price_panel raises when a name has no usable data
            log.warning("skip %s: %s", ticker, exc)
            continue

        res = runner.run(strategy, DataContext.from_prices(panel), benchmark_prices, guardrails=guardrails)
        equity = res.prices
        returns = equity[strategy.name].pct_change().dropna()
        bench = equity[bench_name].pct_change().dropna()
        common = returns.index.intersection(bench.index)
        returns, bench = returns.loc[common], bench.loc[common]

        if len(returns) < min_days or returns.nunique() <= 1:
            log.warning("skip %s: insufficient or flat returns (%d days)", ticker, len(returns))
            continue

        greeks = qs.stats.greeks(returns, bench, prepare_returns=False)
        rows[ticker] = {
            "alpha": float(greeks["alpha"]),
            "beta": float(greeks["beta"]),
            "sharpe": float(qs.stats.sharpe(returns)),
            "total_return": float(qs.stats.comp(returns)),
            "benchmark_return": float(qs.stats.comp(bench)),
        }

    if not rows:
        raise RuntimeError(
            "Sweep produced no results — check the universe, date range, and data source."
        )

    metrics = pd.DataFrame.from_dict(rows, orient="index")
    metrics["excess_return"] = metrics["total_return"] - metrics["benchmark_return"]
    metrics.index.name = "ticker"
    return metrics.sort_values("alpha", ascending=False)
