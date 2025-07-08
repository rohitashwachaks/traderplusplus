# import argparse
# import os
# import pandas as pd
# from core.backtester import Backtester
# from core.data_loader import DataIngestionManager
# from guardrails.trailing_stop_loss import TrailingStopLossGuardrail
# from core.market_data import MarketData
# from core.visualizer import plot_equity_curve, plot_per_asset_equity, plot_equity_with_trades, \
#     plotly_interactive_equity, plot_drawdown
# from strategies.multi_asset.base import StrategyFactory
# from utils.metrics import summarize_metrics
# from contracts.portfolio import Portfolio
# from executors.backtest import BacktestExecutor
# from executors.paper import PaperExecutor
# from executors.live import LiveExecutor
#
# from analytics.performance_evaluator import PerformanceEvaluator
# import yfinance as yf
#
#
# def parse_args():
#     parser = argparse.ArgumentParser(description="Run a backtest, paper, or live trading using Trader++")
#     parser.add_argument("--strategy", type=str, default="momentum", help="Strategy name (e.g. momentum)")
#     parser.add_argument("--tickers", type=str, default="AAPL", help="Comma-separated list of tickers (e.g. AAPL,MSFT)")
#     parser.add_argument("--start", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
#     parser.add_argument("--end", type=str, default="2023-12-31", help="End date (YYYY-MM-DD)")
#     parser.add_argument("--cash", type=float, default=100000.0, help="Starting cash (default: 100000)")
#     parser.add_argument("--source", type=str, default="yahoo", help="Data source: yahoo | polygon")
#     parser.add_argument("--refresh", action="store_true", help="Force data refresh (ignore cache)")
#     parser.add_argument("--export", action="store_true", help="Export trade log and equity curve to CSV")
#     parser.add_argument("--plot", action="store_true", help="Plot equity curve")
#     parser.add_argument("--mode", type=str, default="backtest", choices=["backtest", "paper", "live"],
#                         help="Execution mode: backtest, paper, or live")
#     parser.add_argument("--slippage", type=float, default=0.001, help="Slippage for paper trading (e.g. 0.001 = 0.1%)")
#     parser.add_argument("--broker", type=str, default=None,
#                         help="Broker API module path for live trading (e.g. brokers.alpaca.AlpacaBrokerAPI)")
#     parser.add_argument("--benchmark", type=str, default="SPY", help="Benchmark ticker for performance comparison (default: SPY)")
#     return parser.parse_args()
#
#
# def main():
#     args = parse_args()
#     tickers = [s.strip().upper() for s in args.tickers.split(",")]
#     if args.strategy not in StrategyFactory.get_supported_strategies():
#         raise ValueError(
#             f"Unsupported strategy: {args.strategy}. Supported strategies: {StrategyFactory.get_supported_strategies()}")
#     strategy = StrategyFactory.create_strategy(args.strategy)
#     ingestion = DataIngestionManager(use_cache=True, force_refresh=args.refresh, source=args.source)
#
#     benchmark = args.benchmark.upper()
#     if benchmark.startswith("^"):
#         benchmark = benchmark[1:]  # Remove caret for yfinance compatibility
#
#     market_data = MarketData.from_ingestion(tickers+[benchmark], args.start, args.end, ingestion)
#     guardrails = [TrailingStopLossGuardrail()]
#     portfolio = Portfolio(
#         name=f"{args.strategy.capitalize()}Portfolio",
#         tickers=tickers,
#         benchmark=args.benchmark,
#         starting_cash=args.cash,
#         strategy=strategy,
#         metadata={"source": f"{args.mode.capitalize()}Executor"}
#     )
#     if args.mode == "paper":
#         executor = PaperExecutor(portfolio=portfolio, slippage=args.slippage, market_data=market_data)
#     elif args.mode == "live":
#         if not args.broker:
#             raise ValueError("--broker must be specified for live trading mode (e.g. brokers.alpaca.AlpacaBrokerAPI)")
#         # Dynamically import the broker API module
#         import importlib
#         broker_module, broker_class = args.broker.rsplit('.', 1)
#         broker_api_cls = getattr(importlib.import_module(broker_module), broker_class)
#         broker_api = broker_api_cls()  # User must configure credentials in the broker API implementation
#         executor = LiveExecutor(portfolio=portfolio, broker_api=broker_api, market_data=market_data)
#     else:
#         executor = BacktestExecutor(portfolio=portfolio, market_data=market_data, guardrails=guardrails)
#     bt = Backtester(strategy=strategy, market_data=market_data, portfolio=portfolio, executor=executor)
#     bt.run(tickers=tickers, start_date=args.start, end_date=args.end)
#     equity_curve = bt.get_equity_curve()
#     trade_log = bt.get_trade_log()
#     print(f"\n💰 Starting Cash: ${args.cash:,.2f}")
#     print(f"\n📈 Final Net Worth: ${bt.get_final_net_worth():,.2f}")
#     if args.export:
#         os.makedirs(LOG_DIR, exist_ok=True)
#         equity_curve.to_csv(os.path.join(LOG_DIR, "equity_curve.csv"))
#         trade_log.to_csv(os.path.join(LOG_DIR, "trade_log.csv"))
#         print("✅ Exported equity_curve.csv and trade_log.csv")
#     if args.plot:
#         net_worth_series = equity_curve['net_worth']
#         plot_equity_curve(net_worth_series)
#         plot_drawdown(net_worth_series)
#         plotly_interactive_equity(net_worth_series, trade_log)
#     summarize_metrics(equity_curve=equity_curve, trades_df=trade_log, name=portfolio.name)
#
#     # --- Performance Evaluation ---
#     # Attempt to get a benchmark series (use first ticker if ^SPY not present)
#     try:
#         bench_ticker = portfolio.benchmark if hasattr(portfolio, 'benchmark') else args.benchmark
#         bench_df = yf.download(bench_ticker, start=args.start, end=args.end)
#         benchmark_curve = bench_df['Close']
#         benchmark_curve.index = pd.to_datetime(benchmark_curve.index)
#         benchmark_curve = benchmark_curve.reindex(equity_curve.index, method='ffill')
#         evaluator = PerformanceEvaluator(equity_curve['net_worth'], benchmark_curve)
#         perf_metrics = evaluator.compute_metrics()
#         print("\n=== Strategy vs. Benchmark ===")
#         print(evaluator.summary())
#     except Exception as e:
#         print(f"[WARN] Could not compute benchmark performance: {e}")
#
#
# if __name__ == "__main__":
#     main()
