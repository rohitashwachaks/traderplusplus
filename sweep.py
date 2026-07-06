import argparse
from datetime import datetime

import strategies  # registers built-in strategies
from core.sources import get_source
from core.universe import available as available_universes
from core.universe import create as create_universe
from guardrails.stop_loss import StopLoss
from reporting.manifest import write_manifest
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
    p.add_argument("--cost-bps", type=float, default=0.0,
                   help="Commission+slippage per trade in bps of notional (0 = frictionless, stamped)")
    p.add_argument("--stop-loss", type=float, default=None, help="Stop-loss fraction, e.g. 0.05")
    p.add_argument("--stop-loss-mode", choices=["trailing", "fixed"], default="trailing")
    p.add_argument("--stop-reentry", type=int, default=None, metavar="N",
                   help="Re-enter N trading days after a stop-out if the signal still wants the name")
    return p.parse_args()


def _build_guardrails(args):
    if args.stop_loss is None:
        return []
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing",
                     reentry_days=args.stop_reentry)]


def main():
    args = parse_args()
    strategy = create(args.strategy)
    if not strategy.single_asset:
        raise SystemExit(
            f"'{strategy.name}' is not a single-asset strategy — sweeping pools nothing meaningful. "
            f"Backtest a basket strategy with run.py instead.")

    universe = create_universe(args.universe, limit=args.limit) if args.limit else create_universe(args.universe)
    cost_stamp = ("frictionless: commissions, slippage and short borrow unmodeled — returns are optimistic"
                  if args.cost_bps == 0 else
                  f"costs modeled at {args.cost_bps:g} bps of traded notional; short borrow unmodeled")
    stamps = [s for s in (universe.stamp(), cost_stamp) if s]
    for stamp in stamps:
        log.warning("BIAS: %s", stamp)

    benchmark = clean_ticker(args.benchmark)
    benchmark_prices = get_source("price").load(
        [benchmark], args.start, args.end, source=args.source, interval=args.interval)

    log.info("Sweeping '%s' over %d names (%s to %s)...",
             strategy.name, len(universe.tickers()), args.start, args.end)
    metrics = sweep_universe(
        strategy, universe, benchmark_prices, args.start, args.end,
        source=args.source, interval=args.interval, guardrails=_build_guardrails(args),
        cost_bps=args.cost_bps)

    log.info("Swept %d names with results. Median alpha %.3f, beta %.2f; %.0f%% beat %s.",
             len(metrics), metrics["alpha"].median(), metrics["beta"].median(),
             100 * (metrics["excess_return"] > 0).mean(), benchmark)

    paths = write_distribution_report(metrics, args.out, strategy.name, caveat="; ".join(stamps) or None)
    write_manifest(
        args.out, command="sweep", args=vars(args), strategy=strategy, stamps=stamps,
        universe={"name": universe.name, "biased": universe.biased,
                  "fingerprint": universe.fingerprint()},
        extra={"names_swept": int(len(metrics))},
    )
    for label, path in paths.items():
        log.info("  %-14s %s", label, path)


if __name__ == "__main__":
    main()
