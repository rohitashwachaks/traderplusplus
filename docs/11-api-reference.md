# API Reference

Complete API documentation for all Trader++ classes and methods.

## 🎯 Core Components

### Backtester

**Module**: `core.backtester`

```python
class Backtester:
    def __init__(self, strategy, market_data, portfolio, executor)
    
    def run(self, end_date, start_date=None, interval='1d', period='5y')
    def get_trade_log() -> pd.DataFrame
    def get_equity_curve() -> pd.DataFrame
    def get_final_net_worth() -> float
```

### MarketData

**Module**: `core.market_data`

```python
class MarketData:
    def __init__(self, ingestion_manager, simulation_start_date=None)
    
    def get_market_data(self, tickers, end_date, start_date=None, interval='1d', period='5y')
    def get_price(self, ticker, date, price_type='Close') -> Dict[str, float]
    def get_history(self, ticker_list, end_date, lookback) -> Dict[str, pd.DataFrame]
    def get_series(self, ticker, price_type='Close') -> pd.Series
    
    @property
    def dates -> pd.DatetimeIndex
```

### DataIngestionManager

**Module**: `core.data_loader`

```python
class DataIngestionManager:
    def __init__(self, use_cache=True, force_refresh=False, source="yahoo")
    
    def get_data(self, tickers, end_date, start_date=None, interval='1d', period='5y') -> Dict[str, pd.DataFrame]
```

## 💼 Contracts

### Portfolio

**Module**: `contracts.portfolio`

```python
class Portfolio:
    def __init__(self, name, tickers, starting_cash, strategy, benchmark=None, guardrail=None)
    
    def execute_trade(self, date, order, price, note='Strategy Signal')
    def get_trade_log() -> pd.DataFrame
    def get_position(self, ticker) -> int
    def net_worth(self, prices) -> float
    
    @property
    def cash -> float
    @property
    def positions -> Dict[str, Asset]
```

### Asset

**Module**: `contracts.asset`

```python
class Asset:
    def __init__(self, ticker, shares=0)
    
    def buy(self, shares)
    def sell(self, shares)
    
    @property
    def ticker -> str
    @property
    def shares -> int
```

### Order

**Module**: `contracts.order`

```python
@dataclass
class Order:
    ticker: str
    side: OrderSide
    quantity: float | int
    order_type: OrderType = OrderType.MARKET
```

## 🎨 Strategies

### StrategyBase

**Module**: `strategies.base`

```python
class StrategyBase(ABC):
    @abstractmethod
    def get_name() -> str
    
    @abstractmethod
    def generate_signals(self, price_data, current_date, positions, cash) -> Optional[Dict[str, int]]
```

### StrategyFactory

**Module**: `strategies.base`

```python
class StrategyFactory:
    @classmethod
    def register(cls, name)
    
    @classmethod
    def create_strategy(cls, name, **kwargs) -> StrategyBase
    
    @classmethod
    def get_supported_strategies() -> set
```

## ⚙️ Executors

### BaseExecutor

**Module**: `executors.base`

```python
class BaseExecutor(ABC):
    @abstractmethod
    def submit_order(self, order)
    
    @abstractmethod
    def step(self, current_time)
```

### BacktestExecutor

**Module**: `executors.backtest`

```python
class BacktestExecutor(BaseExecutor):
    def __init__(self, portfolio, market_data)
    
    def get_equity_curve() -> pd.DataFrame
```

## 🛡️ Guardrails

### GuardrailBase

**Module**: `guardrails.base`

```python
class GuardrailBase(ABC):
    @abstractmethod
    def evaluate(self, positions, prices) -> Dict[str, bool]
```

### GuardrailFactory

**Module**: `guardrails.base`

```python
class GuardrailFactory:
    @classmethod
    def register(cls, name)
    
    @classmethod
    def create_guardrail(cls, name, **kwargs) -> GuardrailBase
```

## 📊 Analytics

### PerformanceEvaluator

**Module**: `analytics.performance_evaluator`

```python
class PerformanceEvaluator:
    def __init__(self, portfolio_curve, benchmark_curve, risk_free_rate=0.0)
    
    def compute_metrics() -> Dict[str, float]
    def summary(as_str=True) -> str | Dict
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Contracts & Data Models](./04-contracts.md)
- [Strategy Development](./05-strategies.md)
- [Examples & Tutorials](./12-examples.md)

---

**Code References**: See individual module documentation for detailed API information.
