import pandas as pd

from core.backtester import Backtester
from core.data_loader import load_price_data
from core.visualizer import plot_equity_curve, plot_drawdown
from strategies.stock.base import StrategyFactory
from utils.metrics import summarize_metrics


def main():
    # Setup strategies
    strategies = {
        "momentum": StrategyFactory.create_strategy("momentum", short_window=10, long_window=30)
    }

    # Setup backtester
    backtester = Backtester(data_loader=load_price_data)

    # Run backtest
    backtester.run(
        strategies=strategies,
        symbols=["AAPL", "MSFT", "TSLA"],
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    for res in backtester.get_results():
        summarize_metrics(res.equity_curve, res.trades, f"{res.strategy_name} on {res.symbol}")

    # Overall portfolio
    portfolio_curve = backtester.summarize_portfolio()
    summarize_metrics(portfolio_curve, pd.DataFrame(), "Portfolio")

    # Results
    portfolio_curve = backtester.summarize_portfolio()
    print("\nPortfolio Summary (last 5 days):")
    print(portfolio_curve.tail())

    # Optional: Dump trades per strategy-symbol
    for res in backtester.get_results():
        print(f"\nTrades - {res.strategy_name} on {res.symbol}")
        print(res.trades)
        plot_equity_curve(res.equity_curve, title=f"Equity Curve: {res.strategy_name} on {res.symbol}")
        plot_drawdown(res.equity_curve, title=f"Drawdown: {res.strategy_name} on {res.symbol}")

    # Plot total portfolio
    portfolio_curve = backtester.summarize_portfolio()
    plot_equity_curve(portfolio_curve, title="Total Portfolio Equity Curve")
    plot_drawdown(portfolio_curve, title="Total Portfolio Drawdown")


if __name__ == "__main__":
    main()
