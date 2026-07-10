import argparse
import os
from datetime import datetime

import strategies  # registers built-in strategies
from core.context import build_context
from core.sources import get_source
from core.universe import ListUniverse
from core.universe import available as available_universes
from core.universe import create as create_universe
from engine.runner import run as run_backtest
from guardrails.stop_loss import StopLoss
from reporting.manifest import write_manifest
from reporting.report import write_reports
from strategies.base import available, create
from utils.logger import setup_logger
from utils.utils import clean_ticker

log = setup_logger("traderplusplus")


def parse_args():
    p = argparse.ArgumentParser(description="Backtest a strategy with bt and write reports.")
    p.add_argument("--strategy", default="momentum", choices=available(), help="Strategy name")
    p.add_argument("--tickers", default="SPY", help="Comma-separated tickers, e.g. AAPL,MSFT")
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
    p.add_argument("--cost-bps", type=float, default=0.0,
                   help="Commission+slippage per trade in bps of notional (0 = frictionless, stamped)")
    p.add_argument("--stop-loss", type=float, default=None,
                   help="Stop-loss as a fraction, e.g. 0.05 for 5%% (off by default)")
    p.add_argument("--stop-loss-mode", choices=["trailing", "fixed"], default="trailing",
                   help="Stop from the peak since entry (trailing) or the entry price (fixed)")
    p.add_argument("--stop-reentry", type=int, default=None, metavar="N",
                   help="After a stop-out, re-enter after N trading days if the signal still wants "
                        "the name (default: stay out until the signal itself goes flat and re-fires)")
    p.add_argument("--group-by", default=None,
                   help="Classification key for a grouping strategy: sector | industry | sic2 "
                        "(sic* pulls SIC from EDGAR; overrides the strategy's default)")
    p.add_argument("--rebalance", default=None,
                   help="Override rebalance frequency: D|W|M|Q|Y (default: the strategy's)")
    p.add_argument("--reconstitute", default=None,
                   help="Override reconstitution frequency: D|W|M|Q|Y (default: the strategy's)")
    return p.parse_args()


def _build_guardrails(args):
    if args.stop_loss is None:
        return []
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing",
                     reentry_days=args.stop_reentry)]



def _cost_stamp(cost_bps: float) -> str:
    if cost_bps == 0:
        return "frictionless: commissions, slippage and short borrow unmodeled — returns are optimistic"
    return f"costs modeled at {cost_bps:g} bps of traded notional; short borrow unmodeled"


_CLASSIFICATION_STAMP = ("classification is static — today's GICS/SIC labels applied to all history; "
                         "sector reclassification over time is unmodeled")


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
    if args.group_by:
        strategy.group_by = args.group_by
        strategy.requires_meta = (args.group_by,)
    classify = any(k.startswith("sic") for k in strategy.requires_meta)

    stamps = [s for s in (universe.stamp(), _cost_stamp(args.cost_bps)) if s]
    if strategy.requires_meta:
        stamps.append(_CLASSIFICATION_STAMP)
    for stamp in stamps:
        log.warning("BIAS: %s", stamp)

    guards = _build_guardrails(args)
    guard_panels = tuple(dict.fromkeys(
        name for g in (*strategy.guardrails, *guards) for name in g.requires))
    panels = ("price",) + tuple(strategy.requires) + guard_panels
    log.info("Loading %d names + benchmark %s (%s to %s); panels=%s",
             len(universe.tickers()), benchmark, args.start, args.end, panels)
    ctx = build_context(universe, args.start, args.end, panels=panels,
                        source=args.source, interval=args.interval, classify=classify)

    missing = [k for k in strategy.requires_meta if k not in ctx.meta.columns]
    if missing:
        raise SystemExit(
            f"'{strategy.name}' needs classification {missing}, absent for universe '{universe.name}'. "
            f"GICS keys (sector/industry) exist only for --universe sp500; for any universe use "
            f"--group-by sic2 (EDGAR SIC)."
        )
    benchmark_prices = get_source("price").load(
        [benchmark], args.start, args.end, source=args.source, interval=args.interval)

    if strategy.requires_meta:
        key = strategy.requires_meta[0]
        counts = ctx.meta[key].value_counts()
        log.info("Universe spans %d '%s' groups: %s", len(counts), key,
                 ", ".join(f"{k}×{v}" for k, v in counts.head(12).items()))

    if args.rebalance:
        strategy.rebalance_freq = args.rebalance
    if args.reconstitute:
        strategy.reconstitution_freq = args.reconstitute
    if guards:
        log.info("Guardrails: %s", ", ".join(f"{g.name}({g.pct:.0%},{'trailing' if g.trailing else 'fixed'})" for g in guards))
    log.info("Running '%s' over %d trading days (rebalance=%s, reconstitute=%s)",
             strategy.name, len(ctx.price), strategy.rebalance_freq, strategy.reconstitution_freq)
    res = run_backtest(strategy, ctx, benchmark_prices, initial_capital=args.cash,
                       guardrails=guards, cost_bps=args.cost_bps)

    res.display()
    stop_levels = next(
        (g.levels_ for g in (*strategy.guardrails, *guards) if getattr(g, "levels_", None) is not None),
        None)
    paths = write_reports(res, args.out, strategy.name, benchmark, ctx.price, caveats=stamps,
                          stop_levels=stop_levels)
    if len(ctx.meta.columns):
        paths["classification"] = os.path.join(args.out, "classification.csv")
        ctx.meta.to_csv(paths["classification"])
    write_manifest(
        args.out, command="run", args=vars(args), strategy=strategy, stamps=stamps,
        universe={"name": universe.name, "biased": universe.biased,
                  "fingerprint": universe.fingerprint()},
        extra={"turnover_mean_daily": float(res.backtests[strategy.name].turnover.mean())},
    )
    log.info("Wrote %d artifacts to %s/", len(paths), args.out)
    for label, path in paths.items():
        log.info("  %-14s %s", label, path)


if __name__ == "__main__":
    main()
