from core.backtester import Backtester
from core.data_loader import load_price_data
from strategies.stock.base import StrategyFactory


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

    # Results
    portfolio_curve = backtester.summarize_portfolio()
    print("\nPortfolio Summary (last 5 days):")
    print(portfolio_curve.tail())

    # Optional: Dump trades per strategy-symbol
    for res in backtester.get_results():
        print(f"\nTrades - {res.strategy_name} on {res.symbol}")
        print(res.trades)


if __name__ == "__main__":
    main()