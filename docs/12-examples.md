# Examples & Tutorials

Practical examples and step-by-step tutorials for common use cases.

## 🚀 Example 1: Simple Backtest

```python
from core.backtester import Backtester
from core.market_data import MarketData
from core.data_loader import DataIngestionManager
from contracts.portfolio import Portfolio
from executors.backtest import BacktestExecutor
from analytics.performance_evaluator import PerformanceEvaluator

# Setup Portfolio
portfolio = Portfolio(
    name="Momentum Portfolio",
    tickers="AAPL",
    starting_cash=100000.0,
    strategy="momentum",
    benchmark="SPY"
)

# Setup Data
ingestion = DataIngestionManager(source="yahoo", use_cache=True)
market_data = MarketData(ingestion, simulation_start_date="2023-01-01")

# Setup Executor
executor = BacktestExecutor(portfolio=portfolio, market_data=market_data)

# Run Backtest
backtester = Backtester(
    strategy=portfolio.strategy,
    market_data=market_data,
    portfolio=portfolio,
    executor=executor
)

backtester.run(start_date="2023-01-01", end_date="2024-01-01")

# Results
print(f"Final Net Worth: ${backtester.get_final_net_worth():,.2f}")

# Analyze
evaluator = PerformanceEvaluator(
    backtester.get_equity_curve()['net_worth'],
    backtester.get_equity_curve()['benchmark']
)
print(evaluator.summary())
```

## 📊 Example 2: Strategy Comparison

```python
strategies = ['momentum', 'buy_n_hold']
results = {}

for strategy_name in strategies:
    portfolio = Portfolio(
        name=f"{strategy_name}_portfolio",
        tickers="AAPL",
        starting_cash=100000.0,
        strategy=strategy_name,
        benchmark="SPY"
    )
    
    ingestion = DataIngestionManager(source="yahoo", use_cache=True)
    market_data = MarketData(ingestion, simulation_start_date="2023-01-01")
    executor = BacktestExecutor(portfolio=portfolio, market_data=market_data)
    
    backtester = Backtester(
        strategy=portfolio.strategy,
        market_data=market_data,
        portfolio=portfolio,
        executor=executor
    )
    
    backtester.run(start_date="2023-01-01", end_date="2024-01-01")
    
    evaluator = PerformanceEvaluator(
        backtester.get_equity_curve()['net_worth'],
        backtester.get_equity_curve()['benchmark']
    )
    
    results[strategy_name] = evaluator.compute_metrics()

# Compare
import pandas as pd
comparison = pd.DataFrame(results).T
print(comparison[['portfolio_return', 'sharpe', 'max_drawdown']])
```

## 🛡️ Example 3: Using Guardrails

```python
configs = [
    {"name": "Without Guardrail", "guardrail": None},
    {"name": "With Trailing Stop", "guardrail": "trailing_stop_loss"}
]

for config in configs:
    portfolio = Portfolio(
        name=config['name'],
        tickers="TSLA",
        starting_cash=100000.0,
        strategy="momentum",
        benchmark="SPY",
        guardrail=config['guardrail']
    )
    
    # Run backtest...
    # Compare results
```

## 📈 Example 4: Multi-Asset Portfolio

```python
portfolio = Portfolio(
    name="Tech Portfolio",
    tickers=["AAPL", "MSFT", "GOOGL"],
    starting_cash=300000.0,
    strategy="buy_n_hold",
    benchmark="QQQ"
)

# Run backtest...

# Position breakdown
for ticker, asset in portfolio.positions.items():
    if asset.shares > 0:
        print(f"{ticker}: {asset.shares} shares")
```

## 🎯 Example 5: Custom Strategy

```python
from strategies.base import StrategyBase, StrategyFactory

@StrategyFactory.register("rsi_strategy")
class RSIStrategy(StrategyBase):
    def __init__(self, period=14, oversold=30, overbought=70):
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.lookback_period = period + 1
    
    def get_name(self):
        return f"rsi_{self.period}"
    
    def _calculate_rsi(self, prices):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=self.period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        ticker = list(positions.keys())[0]
        df = price_data[ticker]
        
        rsi = self._calculate_rsi(df['Close'])
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < self.oversold and positions[ticker].shares == 0:
            return {ticker: int(cash / df['Close'].iloc[-1])}
        elif current_rsi > self.overbought and positions[ticker].shares > 0:
            return {ticker: -positions[ticker].shares}
        
        return None

# Test the strategy
portfolio = Portfolio(
    name="RSI Portfolio",
    tickers="AAPL",
    starting_cash=100000.0,
    strategy="rsi_strategy"
)
# Run backtest...
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Strategy Development](./05-strategies.md)
- [Execution Engines](./06-executors.md)
- [Guardrails](./07-guardrails.md)
- [Analytics & Performance](./09-analytics.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`run_backtest.py`](../run_backtest.py)
- [`strategies/`](../strategies/)
