# Execution Engines

Guide to BacktestExecutor, PaperExecutor, and LiveExecutor.

## 📋 Overview

Executors handle order submission, execution, and portfolio state management across different modes:

- **BacktestExecutor**: Historical simulation with perfect fills
- **PaperExecutor**: Live data with simulated execution
- **LiveExecutor**: Real broker integration

## 🎯 BaseExecutor Interface

**Location**: [`executors/base.py`](../executors/base.py)

```python
class BaseExecutor(ABC):
    @abstractmethod
    def submit_order(self, order):
        """Submit an order to the execution engine."""
        pass
    
    @abstractmethod
    def step(self, current_time):
        """Advance simulation or poll live broker."""
        pass
```

## 🔄 BacktestExecutor

**Location**: [`executors/backtest.py`](../executors/backtest.py)

Simulates order execution using historical market data.

### Features
- Perfect fills at historical prices
- No slippage (configurable in future)
- Equity tracking
- Order management

### Usage

```python
from executors.backtest import BacktestExecutor

executor = BacktestExecutor(portfolio=portfolio, market_data=market_data)

backtester = Backtester(
    strategy=portfolio.strategy,
    market_data=market_data,
    portfolio=portfolio,
    executor=executor
)
```

## 📄 PaperExecutor

**Location**: [`executors/paper.py`](../executors/paper.py)

Simulates execution with live data and optional slippage.

### Features
- Live market data
- Slippage simulation
- Realistic fills
- No real money

### Usage

```python
from executors.paper import PaperExecutor

executor = PaperExecutor(
    portfolio=portfolio,
    market_data=market_data,
    slippage=0.001  # 0.1% slippage
)
```

## 🔴 LiveExecutor

**Location**: [`executors/live.py`](../executors/live.py)

Integrates with real broker APIs for live trading.

### Features
- Real broker integration
- Actual order routing
- Portfolio sync
- Fill tracking

### Usage

```python
from executors.live import LiveExecutor
from brokers.alpaca_api import AlpacaBrokerAPI

broker = AlpacaBrokerAPI(api_key="...", secret_key="...")
executor = LiveExecutor(portfolio=portfolio, broker_api=broker)
```

## 🔀 Choosing an Executor

### BacktestExecutor
**Use When**: Testing strategies on historical data
**Pros**: Fast, deterministic, no costs
**Cons**: No slippage, perfect fills

### PaperExecutor
**Use When**: Testing with live data
**Pros**: Live conditions, slippage simulation, safe
**Cons**: Slower, still simulated

### LiveExecutor
**Use When**: Ready for production
**Pros**: Real execution, actual fills
**Cons**: Real money at risk, broker fees

## 💡 Best Practices

1. **Start with Backtest**: Always validate in backtest first
2. **Use Appropriate Slippage**: Model realistic slippage in paper trading
3. **Monitor Order Status**: Track order lifecycle
4. **Handle Errors Gracefully**: Implement retry logic
5. **Sync Portfolio Regularly**: Keep portfolio in sync with broker (live)

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Contracts & Data Models](./04-contracts.md)
- [Strategy Development](./05-strategies.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`executors/base.py`](../executors/base.py)
- [`executors/backtest.py`](../executors/backtest.py)
- [`executors/paper.py`](../executors/paper.py)
- [`executors/live.py`](../executors/live.py)
