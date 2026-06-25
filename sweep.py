import argparse
from datetime import datetime

import strategies  # registers built-in strategies
from core.data_loader import DataIngestionManager
from core.price_panel import to_price_panel
from core.universe import available as available_universes
from core.universe import create as create_universe
from guardrails.stop_loss import StopLoss
from research.report import write_distribution_report
from research.sweep import sweep_universe
from strategies.base import available, create
from utils.logger import setup_logger
from utils.utils import clean_ticker

log = setup_logger("traderplusplus")


def parse_args():
    p = argparse.ArgumentParser(
        description="Sweep a single-asset strategy across a universe and chart the alpha/beta distribution.")
    p.add_argument("--strategy", default="momentum", choices=available(), help="Single-asset strategy")
    p.add_argument("--universe", default="sp500", choices=available_universes(), help="Universe to sweep")
    p.add_argument("--limit", type=int, default=None, help="Sweep only the first N names (for quick runs)")
    p.add_argument("--benchmark", default="SPY", help="Benchmark ticker")
    p.add_argument("--start", default="2018-01-01", help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="End date (YYYY-MM-DD)")
    p.add_argument("--source", default="yahoo", help="Data source: yahoo | polygon | alpaca")
    p.add_argument("--interval", default="1d", help="Bar interval, e.g. 1d")
    p.add_argument("--out", default="output/sweep", help="Directory for report artifacts")
    p.add_argument("--stop-loss", type=float, default=None, help="Stop-loss fraction, e.g. 0.05")
    p.add_argument("--stop-loss-mode", choices=["trailing", "fixed"], default="trailing")
    return p.parse_args()


def _build_guardrails(args):
    if args.stop_loss is None:
        return []
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing")]


def main():
    args = parse_args()
    strategy = create(args.strategy)
    if not strategy.single_asset:
        raise SystemExit(
            f"'{strategy.name}' is not a single-asset strategy — sweeping pools nothing meaningful. "
            f"Backtest a basket strategy with run.py instead.")

    universe = create_universe(args.universe, limit=args.limit) if args.limit else create_universe(args.universe)
    if universe.stamp():
        log.warning("BIAS: %s", universe.stamp())

    benchmark = clean_ticker(args.benchmark)
    benchmark_prices = to_price_panel(
        DataIngestionManager(source=args.source).get_data(
            [benchmark], end_date=args.end, start_date=args.start, interval=args.interval))

    log.info("Sweeping '%s' over %d names (%s to %s)...",
             strategy.name, len(universe.tickers()), args.start, args.end)
    metrics = sweep_universe(
        strategy, universe, benchmark_prices, args.start, args.end,
        source=args.source, interval=args.interval, guardrails=_build_guardrails(args))

    log.info("Swept %d names with results. Median alpha %.3f, beta %.2f; %.0f%% beat %s.",
             len(metrics), metrics["alpha"].median(), metrics["beta"].median(),
             100 * (metrics["excess_return"] > 0).mean(), benchmark)

    paths = write_distribution_report(metrics, args.out, strategy.name, caveat=universe.stamp())
    for label, path in paths.items():
        log.info("  %-14s %s", label, path)


if __name__ == "__main__":
    main()
