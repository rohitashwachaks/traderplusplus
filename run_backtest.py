import argparse
import os

import pandas as pd

from core.backtester import Backtester
from core.data_loader import DataIngestionManager
from core.guardrails.trailing_stop_loss import TrailingStopLossGuardrail
from core.market_data import MarketData
from core.visualizer import plot_equity_curve, plot_per_asset_equity, plot_equity_with_trades, \
    plotly_interactive_equity, plot_drawdown
from strategies.stock.base import StrategyFactory
from strategies.stock.capm_portfolio import CAPMStrategy
from strategies.stock.momentum import MomentumStrategy
from strategies.stock.buy_n_hold import BuyNHoldStrategy
from utils.metrics import summarize_metrics


def parse_args():
    parser = argparse.ArgumentParser(description="Run a backtest using Trader++")

    parser.add_argument("--strategy", type=str, default="momentum", help="Strategy name (e.g. momentum)")
    parser.add_argument("--tickers", type=str, default="AAPL", help="Comma-separated list of tickers (e.g. AAPL,MSFT)")
    parser.add_argument("--start", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2023-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--cash", type=float, default=100000.0, help="Starting cash (default: 100000)")
    parser.add_argument("--source", type=str, default="yahoo", help="Data source: yahoo | polygon")
    parser.add_argument("--refresh", action="store_true", help="Force data refresh (ignore cache)")
    parser.add_argument("--export", action="store_true", help="Export trade log and equity curve to CSV")
    parser.add_argument("--plot", action="store_true", help="Plot equity curve")

    return parser.parse_args()


def main():
    args = parse_args()
    tickers = [s.strip().upper() for s in args.tickers.split(",")]

    # Ensure strategy class is imported before factory call
    if args.strategy not in StrategyFactory.get_supported_strategies():
        raise ValueError(f"Unsupported strategy: {args.strategy}. Supported strategies: {StrategyFactory.get_supported_strategies()}")

    # strategy = StrategyFactory.create_strategy(args.strategy)
    strategy = StrategyFactory.create_strategy(args.strategy, short_window=10, long_window=20)
    # ingestion = DataIngestionManager(
    #     use_cache=True,
    #     force_refresh=args.refresh,
    #     source=args.source
    # )

    ingestion = DataIngestionManager(use_cache=True, force_refresh=args.refresh, source=args.source)
    market_data = MarketData.from_ingestion(tickers, args.start, args.end, ingestion)

    guardrails = [TrailingStopLossGuardrail()]

    bt = Backtester(strategy=strategy, market_data=market_data, starting_cash=args.cash, guardrails=guardrails)
    bt.run(tickers=tickers, start_date=args.start, end_date=args.end)

    # Results
    equity_curve = bt.get_equity_curve()
    trade_log = bt.get_trade_log()

    print(f"\n💰 Starting Cash: ${args.cash:,.2f}")
    print(f"\n📈 Final Net Worth: ${bt.get_final_net_worth():,.2f}")
    summarize_metrics(equity_curve=equity_curve, trades_df=trade_log, name="Portfolio")

    if args.export:
        os.makedirs('./logs', exist_ok=True)
        equity_curve.to_csv("./logs/equity_curve.csv")
        trade_log.to_csv("./logs/trade_log.csv")
        print("✅ Exported equity_curve.csv and trade_log.csv")

    if args.plot:
        net_worth_series = equity_curve['net_worth']

        # 🚨 Sanitize it
        net_worth_series = pd.to_numeric(net_worth_series, errors="coerce").astype(float)
        net_worth_series = net_worth_series.dropna()
        net_worth_series.index = pd.to_datetime(net_worth_series.index)

        market_data = bt.get_market_data()

        plot_per_asset_equity(bt.portfolio.position_history, market_data)
        plot_equity_with_trades(equity_curve['net_worth'], trade_log)
        plot_drawdown(equity_curve['net_worth'])
        plotly_interactive_equity(equity_curve['net_worth'], trade_log)


if __name__ == "__main__":
    main()
