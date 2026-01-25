# Contracts & Data Models

Fundamental data structures: Portfolio, Asset, Order, and their relationships.

## 💼 Portfolio

**Location**: [`contracts/portfolio.py`](../contracts/portfolio.py)

Central data structure tracking positions, cash, and trading activity.

### Key Methods

#### `execute_trade(date, order, price, note='Strategy Signal')`
Executes a trade and updates portfolio state.

#### `get_trade_log() -> pd.DataFrame`
Returns complete trade history.

#### `get_position(ticker) -> int`
Returns current shares held for a ticker.

#### `net_worth(prices) -> float`
Calculates total portfolio value.

### Properties

- `cash -> float`: Current cash balance
- `positions -> Dict[str, Asset]`: Current positions

### Usage Example

```python
from contracts.portfolio import Portfolio

portfolio = Portfolio(
    name="Growth Portfolio",
    tickers=["AAPL", "MSFT"],
    starting_cash=100000.0,
    strategy="momentum",
    benchmark="SPY"
)

print(f"Cash: ${portfolio.cash:,.2f}")
print(f"Positions: {portfolio.positions}")
```

## 📦 Asset Classes

**Location**: [`contracts/asset.py`](../contracts/asset.py)

### Asset
Represents tradable securities with integer shares.

```python
aapl = Asset(ticker="AAPL", shares=0)
aapl.buy(10)  # Buy 10 shares
aapl.sell(5)  # Sell 5 shares
```

### CashAsset
Represents cash reserves with float precision.

```python
cash = CashAsset(initial_cash=100000.0)
cash.deposit_cash(5000.0)
cash.withdraw_cash(1250.75)
```

## 📝 Order System

**Location**: [`contracts/order.py`](../contracts/order.py)

### Order
Dataclass representing a trade order.

```python
from contracts.order import Order, OrderSide, OrderType

order = Order(
    ticker="AAPL",
    side=OrderSide.BUY,
    quantity=100,
    order_type=OrderType.MARKET
)
```

### OrderResult
Captures order execution results.

```python
from contracts.order import OrderResult, OrderStatus

result = OrderResult(
    order_id="abc-123",
    status=OrderStatus.FILLED,
    filled_quantity=100.0,
    avg_fill_price=125.50
)
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Strategy Development](./05-strategies.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`contracts/portfolio.py`](../contracts/portfolio.py)
- [`contracts/asset.py`](../contracts/asset.py)
- [`contracts/order.py`](../contracts/order.py)
