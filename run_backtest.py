import argparse
import os
from typing import Optional

from analytics.performance_evaluator import PerformanceEvaluator
from core.backtester import Backtester
from executors.backtest import BacktestExecutor
from core.data_loader import DataIngestionManager
# from guardrails.trailing_stop_loss import TrailingStopLossGuardrail
from core.market_data import MarketData
from contracts.portfolio import Portfolio
from core.visualizer import plot_drawdown, plotly_equity_vs_benchmark


def parse_args():
    parser = argparse.ArgumentParser(description="Run a backtest, paper, or live trading using Trader++")
    parser.add_argument("--strategy", type=str, default="momentum", help="Strategy name (e.g. momentum)")
    parser.add_argument("--tickers", type=str, default="AAPL", help="Comma-separated list of tickers (e.g. AAPL,MSFT)")
    parser.add_argument("--start", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2023-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--cash", type=float, default=100000.0, help="Starting cash (default: 100000)")
    parser.add_argument("--benchmark", type=str, default="SPY", help="Benchmark ticker for performance comparison (default: SPY)")
    parser.add_argument("--guardrail", type=Optional[str], default=None, help="Guardrail strategy (e.g. trailing_stop_loss)")
    parser.add_argument("--source", type=str, default="yahoo", help="Data source: yahoo | polygon")
    parser.add_argument("--refresh", action="store_true", help="Force data refresh (ignore cache)")
    parser.add_argument("--export", action="store_true", help="Export trade log and equity curve to CSV")
    parser.add_argument("--plot", action="store_true", help="Plot equity curve")
    parser.add_argument("--mode", type=str, default="backtest", choices=["backtest", "paper", "live"],
                        help="Execution mode: backtest, paper, or live")
    parser.add_argument("--slippage", type=float, default=0.001, help="Slippage for paper trading (e.g. 0.001 = 0.1%)")
    parser.add_argument("--broker", type=str, default=None,
                        help="Broker API module path for live trading (e.g. brokers.alpaca.AlpacaBrokerAPI)")
    return parser.parse_args()


def main():
    args = parse_args()

    # --- Portfolio Setup ---
    portfolio = Portfolio(
        name=f"{args.strategy.capitalize()}-Portfolio",
        tickers=args.tickers,
        benchmark=args.benchmark,
        starting_cash=args.cash,
        strategy=args.strategy,
        guardrail=args.guardrail,
        metadata={"source": f"{args.mode.capitalize()}Executor"}
    )
    tickers = portfolio.tickers
    strategy = portfolio.strategy

    # --- Market Data Setup ---
    ingestion = DataIngestionManager(source=args.source)
    market_data = MarketData(ingestion, simulation_start_date=args.start)

    # --- Executor Setup ---
    executor = BacktestExecutor(portfolio=portfolio, market_data=market_data)

    # --- Backtester Setup ---
    bt = Backtester(strategy=strategy, market_data=market_data, portfolio=portfolio, executor=executor)
    bt.run(start_date=args.start, end_date=args.end)

    # --- Backtest Results ---
    print(f"\n🚀 Backtest completed for {portfolio.name} with {len(tickers)} tickers ({', '.join(tickers)}) from {args.start} to {args.end}")
    print(f"💰 Starting Cash: ${args.cash:,.2f}")
    print(f"📈 Final Net Worth: ${bt.get_final_net_worth():,.2f}")

    equity_curve = bt.get_equity_curve()
    trade_log = bt.get_trade_log()
    if args.export:
        os.makedirs('./logs', exist_ok=True)
        equity_curve.to_csv("./logs/equity_curve.csv")
        trade_log.to_csv("./logs/trade_log.csv")
        print("✅ Exported equity_curve.csv and trade_log.csv")
    if args.plot:
        net_worth_series = equity_curve['net_worth']
        benchmark_series = equity_curve['benchmark']
        plot_drawdown(net_worth_series)
        plotly_equity_vs_benchmark(net_worth_series, benchmark_series, trade_logs=trade_log)

    # --- Performance Evaluation ---
    try:
        evaluator = PerformanceEvaluator(equity_curve['net_worth'], equity_curve['benchmark'])
        print("\n=== Strategy vs. Benchmark ===")
        print(evaluator.summary())
    except Exception as e:
        print(f"[WARN] Could not compute benchmark performance: {e}")


if __name__ == "__main__":
    main()
