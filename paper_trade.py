import argparse
from dataclasses import asdict
from datetime import datetime, timedelta

import strategies  # registers built-in strategies
from core.context import DataContext
from core.sources import get_source
from engine import journal
from engine.paper import build_plan, execute_plan, format_plan, reconcile
from engine.runner import target_weights
from guardrails.stop_loss import StopLoss
from strategies.base import available, create
from utils.logger import setup_logger
from utils.utils import clean_ticker

log = setup_logger("traderplusplus")


def parse_args():
    p = argparse.ArgumentParser(
        description="Rebalance an Alpaca paper account toward a strategy's current target weights.")
    p.add_argument("--strategy", default="momentum", choices=available())
    p.add_argument("--tickers", default="AAPL", help="Comma-separated tickers")
    p.add_argument("--start", default=None, help="History start (YYYY-MM-DD); default ~1y back")
    p.add_argument("--source", default="yahoo", help="Data source: yahoo | polygon | alpaca")
    p.add_argument("--interval", default="1d", help="Bar interval, e.g. 1d")
    p.add_argument("--stop-loss", type=float, default=None, help="Stop-loss fraction, e.g. 0.05")
    p.add_argument("--stop-loss-mode", choices=["trailing", "fixed"], default="trailing")
    p.add_argument("--stop-reentry", type=int, default=None, metavar="N",
                   help="Re-enter N trading days after a stop-out if the signal still wants the name")
    p.add_argument("--rebalance", default=None, help="Rebalance frequency override: D|W|M|Q|Y")
    p.add_argument("--reconstitute", default=None, help="Reconstitution frequency override: D|W|M|Q|Y")
    p.add_argument("--journal", default="output/paper/journal.jsonl",
                   help="Append-only JSONL journal of plans, executions and reconciliations")
    p.add_argument("--execute", action="store_true",
                   help="Actually submit orders to Alpaca paper (default: preview only)")
    p.add_argument("--reconcile", action="store_true",
                   help="Compare the last executed plan against the broker's fills and exit")
    return p.parse_args()


def _build_strategy(args):
    strategy = create(args.strategy)
    if args.rebalance:
        strategy.rebalance_freq = args.rebalance
    if args.reconstitute:
        strategy.reconstitution_freq = args.reconstitute
    return strategy


def _build_guardrails(args):
    if args.stop_loss is None:
        return []
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing",
                     reentry_days=args.stop_reentry)]


def _broker():
    # Import here so missing Alpaca creds only matter when actually talking to the broker.
    from brokers.alpaca import AlpacaBroker
    return AlpacaBroker()


def _reconcile(args) -> None:
    executed = journal.last(args.journal, "executed")
    if executed is None:
        raise SystemExit(f"No executed plan in {args.journal} — nothing to reconcile.")
    broker = _broker()
    report = reconcile(executed["orders"], broker.orders(since=executed["ts"]),
                       executed["prices"])
    print(report.to_string(index=False))
    journal.record(args.journal, "reconciliation", {
        "against_ts": executed["ts"],
        "rows": report.to_dict("records"),
    })
    bad = report[report["status"].isin(["missing", "unplanned"])]
    if not bad.empty:
        log.warning("Reconciliation found %d missing/unplanned order(s) — investigate.", len(bad))


def main():
    args = parse_args()
    if args.reconcile:
        _reconcile(args)
        return

    tickers = [clean_ticker(t) for t in args.tickers.split(",")]
    end = datetime.now().strftime("%Y-%m-%d")
    start = args.start or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    prices = get_source("price").load(tickers, start, end, source=args.source, interval=args.interval)
    ctx = DataContext.from_prices(prices)

    strategy = _build_strategy(args)
    weights = target_weights(strategy, ctx, _build_guardrails(args)).ffill()
    target = weights.iloc[-1]
    latest_prices = prices.iloc[-1]
    log.info("Target weights as of %s: %s", prices.index[-1].date(),
             ", ".join(f"{t} {w:.0%}" for t, w in target.items() if w > 1e-4) or "all cash")

    broker = _broker()
    equity = broker.equity()
    positions = broker.positions()

    plan = build_plan(target, latest_prices, positions, equity)
    print(format_plan(plan, equity))

    payload = {
        "strategy": strategy.name,
        "tickers": tickers,
        "equity": equity,
        "as_of": str(prices.index[-1].date()),
        "prices": {t: float(latest_prices[t]) for t in latest_prices.index},
        "orders": [asdict(o) for o in plan],
    }
    if not plan:
        journal.record(args.journal, "noop", payload)
        return
    if args.execute:
        execute_plan(broker, plan)
        journal.record(args.journal, "executed", payload)
        log.info("Done. Orders submitted to Alpaca paper and journaled to %s "
                 "— run --reconcile after fills settle.", args.journal)
    else:
        journal.record(args.journal, "preview", payload)
        log.info("Preview only — re-run with --execute to submit these orders.")


if __name__ == "__main__":
    main()
