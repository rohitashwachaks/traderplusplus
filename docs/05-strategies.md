# Strategy Development

Complete guide to creating custom trading strategies in Trader++.

## 🎯 StrategyBase Interface

**Location**: [`strategies/base.py`](../strategies/base.py)

All strategies must inherit from `StrategyBase`:

```python
from strategies.base import StrategyBase, StrategyFactory

class StrategyBase(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Return unique strategy name."""
        pass
    
    @abstractmethod
    def generate_signals(
        self,
        price_data: pd.DataFrame | Dict[str, pd.DataFrame],
        current_date: pd.Timestamp,
        positions: Dict[str, Asset],
        cash: float,
        **kwargs
    ) -> Optional[Dict[str, int]]:
        """Generate trading signals."""
        pass
```

## 🏗️ Creating a Strategy

### Step 1: Define the Class

```python
@StrategyFactory.register("my_strategy")
class MyStrategy(StrategyBase):
    def __init__(self, param1=10):
        super().__init__()
        self.param1 = param1
        self.lookback_period = param1
    
    def get_name(self):
        return f"my_strategy_{self.param1}"
```

### Step 2: Implement Signal Logic

```python
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        signals = {}
        
        for ticker, df in price_data.items():
            if self._should_buy(df):
                shares = int(cash / df['Close'].iloc[-1])
                signals[ticker] = shares
            elif self._should_sell(df, positions[ticker]):
                signals[ticker] = -positions[ticker].shares
        
        return signals if signals else None
```

## 📚 Built-in Strategies

### Buy & Hold
**Location**: [`strategies/single_asset/buy_n_hold.py`](../strategies/single_asset/buy_n_hold.py)

Buys once and holds forever.

```bash
python run_backtest.py --strategy=buy_n_hold --tickers=AAPL
```

### Momentum
**Location**: [`strategies/single_asset/momentum.py`](../strategies/single_asset/momentum.py)

Moving average crossover strategy.

```bash
python run_backtest.py --strategy=momentum --tickers=AAPL
```

## 🎨 Strategy Patterns

### Single-Asset Strategy

```python
@StrategyFactory.register("single_asset_example")
class SingleAssetStrategy(StrategyBase):
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        ticker = list(positions.keys())[0]
        df = price_data[ticker]
        
        if self._buy_condition(df):
            return {ticker: self._calculate_shares(cash, df)}
        elif self._sell_condition(df):
            return {ticker: -positions[ticker].shares}
        
        return None
```

### Multi-Asset Strategy

```python
@StrategyFactory.register("multi_asset_example")
class MultiAssetStrategy(StrategyBase):
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        signals = {}
        
        for ticker, df in price_data.items():
            score = self._calculate_score(df)
            signals[ticker] = score
        
        return self._allocate_capital(signals, cash, positions)
```

## 💡 Best Practices

1. **Validate Input Data**: Check for sufficient data before processing
2. **Handle Edge Cases**: Deal with NaN values and zero prices
3. **Use Vectorized Operations**: Prefer pandas operations over loops
4. **Document Your Strategy**: Add docstrings and comments
5. **Avoid Look-Ahead Bias**: Only use data up to `current_date`

## 🧪 Testing Strategies

```python
import unittest

class TestMyStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MyStrategy()
    
    def test_buy_signal(self):
        signals = self.strategy.generate_signals(...)
        self.assertIsNotNone(signals)
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Contracts & Data Models](./04-contracts.md)
- [Examples & Tutorials](./12-examples.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`strategies/base.py`](../strategies/base.py)
- [`strategies/single_asset/`](../strategies/single_asset/)
- [`strategies/multi_asset/`](../strategies/multi_asset/)
