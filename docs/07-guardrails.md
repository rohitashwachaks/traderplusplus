# Risk Management & Guardrails

Guide to implementing risk controls and protective mechanisms.

## 📋 Overview

Guardrails are risk management modules that can:
- Monitor positions and track performance
- Enforce rules and automatically exit positions
- Prevent losses with stop-losses
- Manage portfolio-level risk

**Location**: [`guardrails/`](../guardrails/)

## 🎯 GuardrailBase Interface

**Location**: [`guardrails/base.py`](../guardrails/base.py)

```python
class GuardrailBase(ABC):
    @abstractmethod
    def evaluate(self, positions: Dict[str, int], prices: Dict[str, float]) -> Dict[str, bool]:
        """
        Evaluate which positions should be exited.
        
        Returns:
            Dict mapping ticker to True if position should be force-sold
        """
        pass
```

## 🛡️ Built-in Guardrails

### Trailing Stop Loss

**Location**: [`guardrails/trailing_stop_loss.py`](../guardrails/trailing_stop_loss.py)

Implements a trailing stop-loss that locks in profits.

```python
@GuardrailFactory.register("trailing_stop_loss")
class TrailingStopLossGuardrail(GuardrailBase):
    def __init__(self, stop_pct: float = 0.07):
        self.stop_pct = stop_pct  # 7% default
        self.entry_prices = {}
        self.highest_since_entry = {}
```

**Usage**:
```python
portfolio = Portfolio(
    name="Protected Portfolio",
    tickers="AAPL",
    starting_cash=100000,
    strategy="momentum",
    guardrail="trailing_stop_loss"
)
```

**CLI**:
```bash
python run_backtest.py --guardrail=trailing_stop_loss --tickers=AAPL
```

## 🏗️ Creating Custom Guardrails

### Step 1: Define the Class

```python
from guardrails.base import GuardrailBase, GuardrailFactory

@GuardrailFactory.register("my_guardrail")
class MyGuardrail(GuardrailBase):
    def __init__(self, param1=0.1):
        super().__init__()
        self.param1 = param1
```

### Step 2: Implement Evaluation Logic

```python
    def evaluate(self, positions, prices):
        exits = {}
        
        for ticker, asset in positions.items():
            if ticker == 'CASH' or asset.shares <= 0:
                continue
            
            current_price = prices.get(ticker, 0)
            
            if self._should_exit(ticker, current_price, asset):
                exits[ticker] = True
        
        return exits
```

## 📚 Guardrail Patterns

### Fixed Stop Loss

```python
@GuardrailFactory.register("fixed_stop_loss")
class FixedStopLossGuardrail(GuardrailBase):
    def __init__(self, stop_pct: float = 0.05):
        self.stop_pct = stop_pct
        self.entry_prices = {}
    
    def evaluate(self, positions, prices):
        exits = {}
        for ticker, asset in positions.items():
            if ticker == 'CASH' or asset.shares <= 0:
                continue
            
            current_price = prices.get(ticker, 0)
            entry_price = self.entry_prices.get(ticker, 0)
            loss_pct = (current_price - entry_price) / entry_price
            
            if loss_pct < -self.stop_pct:
                exits[ticker] = True
        
        return exits
```

### Take Profit

```python
@GuardrailFactory.register("take_profit")
class TakeProfitGuardrail(GuardrailBase):
    def __init__(self, profit_pct: float = 0.20):
        self.profit_pct = profit_pct
        self.entry_prices = {}
    
    def evaluate(self, positions, prices):
        exits = {}
        for ticker, asset in positions.items():
            if ticker == 'CASH' or asset.shares <= 0:
                continue
            
            current_price = prices.get(ticker, 0)
            entry_price = self.entry_prices.get(ticker, 0)
            profit_pct = (current_price - entry_price) / entry_price
            
            if profit_pct >= self.profit_pct:
                exits[ticker] = True
        
        return exits
```

## 💡 Best Practices

1. **Track Entry Prices**: Always track entry prices for calculations
2. **Clean Up on Exit**: Remove tracking when positions close
3. **Handle Edge Cases**: Skip cash, empty positions, missing prices
4. **Log Actions**: Print when guardrails trigger
5. **Combine Guardrails**: Use multiple guardrails together

## 📊 Performance Impact

Guardrails typically:
- Reduce max drawdown
- Lower returns (may exit winners early)
- Improve Sharpe ratio
- Increase trade count

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Strategy Development](./05-strategies.md)
- [Execution Engines](./06-executors.md)
- [Examples & Tutorials](./12-examples.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`guardrails/base.py`](../guardrails/base.py)
- [`guardrails/trailing_stop_loss.py`](../guardrails/trailing_stop_loss.py)
