import argparse
from datetime import datetime

import strategies  # registers built-in strategies
from core.data_loader import DataIngestionManager
from core.price_panel import to_price_panel
from engine.runner import run as run_backtest
from reporting.report import write_reports
from strategies.base import available, create
from utils.logger import setup_logger
from utils.utils import clean_ticker

log = setup_logger("traderplusplus")


def parse_args():
    p = argparse.ArgumentParser(description="Backtest a strategy with bt and write reports.")
    p.add_argument("--strategy", default="momentum", choices=available(), help="Strategy name")
    p.add_argument("--tickers", default="AAPL", help="Comma-separated tickers, e.g. AAPL,MSFT")
    p.add_argument("--benchmark", default="SPY", help="Benchmark ticker")
    p.add_argument("--start", default="2023-01-01", help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"), help="End date (YYYY-MM-DD)")
    p.add_argument("--cash", type=float, default=100_000.0, help="Starting capital")
    p.add_argument("--source", default="yahoo", help="Data source: yahoo | polygon | alpaca")
    p.add_argument("--interval", default="1d", help="Bar interval, e.g. 1d")
    p.add_argument("--out", default="output", help="Directory for report artifacts")
    return p.parse_args()


def _load_panel(ingestion, tickers, start, end, interval):
    data = ingestion.get_data(tickers, end_date=end, start_date=start, interval=interval)
    return to_price_panel(data)


def main():
    args = parse_args()
    tickers = [clean_ticker(t) for t in args.tickers.split(",")]
    benchmark = clean_ticker(args.benchmark)

    ingestion = DataIngestionManager(source=args.source)
    log.info("Loading %s and benchmark %s (%s to %s)", tickers, benchmark, args.start, args.end)
    prices = _load_panel(ingestion, tickers, args.start, args.end, args.interval)
    benchmark_prices = _load_panel(ingestion, [benchmark], args.start, args.end, args.interval)

    strategy = create(args.strategy)
    log.info("Running '%s' over %d trading days", strategy.name, len(prices))
    res = run_backtest(strategy, prices, benchmark_prices, initial_capital=args.cash)

    res.display()
    paths = write_reports(res, args.out, strategy.name, benchmark)
    log.info("Wrote %d artifacts to %s/", len(paths), args.out)
    for label, path in paths.items():
        log.info("  %-14s %s", label, path)


if __name__ == "__main__":
    main()
