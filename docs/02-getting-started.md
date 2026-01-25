# Getting Started with Trader++

## 📋 Prerequisites

- **Python**: 3.8 or higher
- **Operating System**: macOS, Linux, or Windows
- **Basic Knowledge**: Python, pandas, basic trading concepts

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/traderplusplus.git
cd traderplusplus
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python -c "import pandas, numpy, yfinance; print('✅ Installation successful!')"
```

## 🚀 Your First Backtest

### Using the CLI

```bash
python run_backtest.py \
    --strategy=momentum \
    --tickers=AAPL \
    --start=2023-01-01 \
    --end=2024-01-01 \
    --cash=100000 \
    --benchmark=SPY \
    --plot \
    --export
```

### Python Script

```python
from core.backtester import Backtester
from core.market_data import MarketData
from core.data_loader import DataIngestionManager
from contracts.portfolio import Portfolio
from executors.backtest import BacktestExecutor

# Setup Portfolio
portfolio = Portfolio(
    name="My First Portfolio",
    tickers="AAPL",
    starting_cash=100000.0,
    strategy="buy_n_hold",
    benchmark="SPY"
)

# Setup Market Data
ingestion = DataIngestionManager(source="yahoo")
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

# View Results
print(f"Final Net Worth: ${backtester.get_final_net_worth():,.2f}")
print(backtester.get_trade_log())
```

## 📊 Understanding the Output

### Trade Log
```
                ticker  action  shares    price  cash_remaining
date                                                            
2023-01-03      AAPL     BUY      100   125.07      87493.00
2023-02-15      AAPL    SELL      100   155.33     102993.00
```

### Equity Curve
```
                net_worth  benchmark
date                                
2023-01-03      100000.00     100.00
2023-01-04      101250.00     100.50
```

### Performance Metrics
```
portfolio_return: 0.1523
sharpe: 0.6934
alpha: 0.0234
max_drawdown: -0.1523
```

## 🎯 Basic Workflow

1. **Define Your Strategy**: Choose from built-in or create custom
2. **Configure Portfolio**: Set tickers, cash, strategy, guardrails
3. **Setup Data Source**: Yahoo Finance, Alpaca, or Polygon
4. **Choose Execution Mode**: Backtest, Paper, or Live
5. **Run and Analyze**: Execute and evaluate results

## 🐛 Troubleshooting

### Data Download Issues
- Check ticker symbol is valid
- Verify date range has trading days
- Try `--refresh` to force data re-download

### Import Errors
- Ensure you're in the project root directory
- Add project to PYTHONPATH if needed

### Strategy Not Found
- Check strategy is registered in `strategies/__init__.py`
- Verify `@StrategyFactory.register("name")` decorator

## 📚 Next Steps

1. **Learn Strategy Development**: [Strategy Development Guide](./05-strategies.md)
2. **Understand Core Components**: [Core Components](./03-core-components.md)
3. **Explore Examples**: [Examples & Tutorials](./12-examples.md)

---

**Related Documentation**:
- [Overview & Architecture](./01-overview-architecture.md)
- [Strategy Development](./05-strategies.md)
- [Examples & Tutorials](./12-examples.md)
