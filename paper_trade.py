import argparse
from datetime import datetime, timedelta

import strategies  # registers built-in strategies
from core.context import DataContext
from core.data_loader import DataIngestionManager
from core.price_panel import to_price_panel
from engine.paper import build_plan, execute_plan, format_plan
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
    p.add_argument("--rebalance", default=None, help="Rebalance frequency override: D|W|M|Q|Y")
    p.add_argument("--reconstitute", default=None, help="Reconstitution frequency override: D|W|M|Q|Y")
    p.add_argument("--execute", action="store_true",
                   help="Actually submit orders to Alpaca paper (default: preview only)")
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
    return [StopLoss(pct=args.stop_loss, trailing=args.stop_loss_mode == "trailing")]


def main():
    args = parse_args()
    tickers = [clean_ticker(t) for t in args.tickers.split(",")]
    end = datetime.now().strftime("%Y-%m-%d")
    start = args.start or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    ingestion = DataIngestionManager(source=args.source)
    prices = to_price_panel(ingestion.get_data(tickers, end_date=end, start_date=start, interval=args.interval))
    ctx = DataContext.from_prices(prices)

    strategy = _build_strategy(args)
    weights = target_weights(strategy, ctx, _build_guardrails(args)).ffill()
    target = weights.iloc[-1]
    latest_prices = prices.iloc[-1]
    log.info("Target weights as of %s: %s", prices.index[-1].date(),
             ", ".join(f"{t} {w:.0%}" for t, w in target.items() if w > 1e-4) or "all cash")

    # Import here so a missing alpaca-py / creds only matters when actually trading.
    from brokers.alpaca import AlpacaBroker
    broker = AlpacaBroker()
    equity = broker.equity()
    positions = broker.positions()

    plan = build_plan(target, latest_prices, positions, equity)
    print(format_plan(plan, equity))

    if not plan:
        return
    if args.execute:
        execute_plan(broker, plan)
        log.info("Done. Orders submitted to Alpaca paper.")
    else:
        log.info("Preview only — re-run with --execute to submit these orders.")


if __name__ == "__main__":
    main()
