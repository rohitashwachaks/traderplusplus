import argparse
from datetime import datetime

import strategies  # registers built-in strategies
from core.context import build_context
from core.data_loader import DataIngestionManager
from core.price_panel import to_price_panel
from core.universe import ListUniverse
from core.universe import available as available_universes
from core.universe import create as create_universe
from engine.runner import run as run_backtest
from guardrails.stop_loss import StopLoss
from reporting.report import write_reports
from strategies.base import available, create
from utils.logger import setup_logger
from utils.utils import clean_ticker

log = setup_logger("traderplusplus")


def parse_args():
    p = argparse.ArgumentParser(description="Backtest a strategy with bt and write reports.")
    p.add_argument("--strategy", default="momentum", choices=available(), help="Strategy name")
    p.add_argument("--tickers", default="AAPL", help="Comma-separated tickers, e.g. AAPL,MSFT")
    p.add_argument("--universe", default=None, choices=available_universes(),
                   help="Trade a named universe (e.g. sp500) instead of --tickers")
    p.add_argument("--limit", type=int, default=None,
                   help="With --universe, use only the first N names (quick runs)")
    p.add_argument("--benchmark", default="SPY", help="Benchmark ticker")
    p.add_argument("--start", default="2023-01-01", help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="End date (YYYY-MM-DD)")
    p.add_argument("--cash", type=float, default=100_000.0, help="Starting capital")
    p.add_argument("--source", default="yahoo", help="Data source: yahoo | polygon | alpaca")
    p.add_argument("--interval", default="1d", help="Bar interval, e.g. 1d")
    p.add_argument("--out", default="output", help="Directory for report artifacts")
    p.add_argument("--stop-loss", type=float, default=None,
                   help="Stop-loss as a fraction, e.g. 0.05 for 5%% (off by default)")
    p.add_argument("--stop-loss-mode", choices=["trailing", "fixed"], default="trailing",
                   help="Stop from the peak since entry (trailing) or the entry price (fixed)")
    p.add_argument("--rebalance", default=None,
                   help="Override rebalance frequency: D|W|M|Q|Y (default: the strategy's)")
    p.add_argument("--reconstitute", default=None,
                   help="Override reconstitution frequency: D|W|M|Q|Y (default: the strategy's)")
    return p.parse_args()


def _build_guardrails(args):
    if args.stop_loss is None:
        return []
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing")]


def _load_panel(ingestion, tickers, start, end, interval):
    data = ingestion.get_data(tickers, end_date=end, start_date=start, interval=interval)
    return to_price_panel(data)


def main():
    args = parse_args()
    benchmark = clean_ticker(args.benchmark)

    if args.universe:
        universe = create_universe(args.universe, limit=args.limit) if args.limit else create_universe(args.universe)
    else:
        universe = ListUniverse(args.tickers.split(","))

    strategy = create(args.strategy)
    if strategy.single_asset and len(universe.tickers()) > 1:
        raise SystemExit(
            f"'{strategy.name}' is a single-asset strategy — pooling many names into one run is meaningless. "
            f"Sweep it across the universe instead, e.g.:\n"
            f"  python sweep.py --strategy={strategy.name} "
            f"--universe={args.universe or 'sp500'} --benchmark={benchmark}"
        )
    if universe.stamp():
        log.warning("BIAS: %s", universe.stamp())

    panels = ("price",) + tuple(strategy.requires)
    log.info("Loading %d names + benchmark %s (%s to %s); panels=%s",
             len(universe.tickers()), benchmark, args.start, args.end, panels)
    ctx = build_context(universe, args.start, args.end, panels=panels,
                        source=args.source, interval=args.interval)
    benchmark_prices = _load_panel(
        DataIngestionManager(source=args.source), [benchmark], args.start, args.end, args.interval)

    if args.rebalance:
        strategy.rebalance_freq = args.rebalance
    if args.reconstitute:
        strategy.reconstitution_freq = args.reconstitute
    guards = _build_guardrails(args)
    if guards:
        log.info("Guardrails: %s", ", ".join(f"{g.name}({g.pct:.0%},{'trailing' if g.trailing else 'fixed'})" for g in guards))
    log.info("Running '%s' over %d trading days (rebalance=%s, reconstitute=%s)",
             strategy.name, len(ctx.price), strategy.rebalance_freq, strategy.reconstitution_freq)
    res = run_backtest(strategy, ctx, benchmark_prices, initial_capital=args.cash, guardrails=guards)

    res.display()
    paths = write_reports(res, args.out, strategy.name, benchmark, ctx.price)
    log.info("Wrote %d artifacts to %s/", len(paths), args.out)
    for label, path in paths.items():
        log.info("  %-14s %s", label, path)


if __name__ == "__main__":
    main()
