# Advanced Topics

Advanced features and techniques for power users.

## 📋 Overview

- Multi-asset strategies
- Derivatives trading
- ML integration
- Performance optimization
- Live trading deployment

## 🎯 Multi-Asset Portfolio Strategies

### Portfolio Optimization

```python
@StrategyFactory.register("mean_variance")
class MeanVarianceStrategy(StrategyBase):
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        # Calculate returns
        returns = {ticker: df['Close'].pct_change() for ticker, df in price_data.items()}
        returns_df = pd.DataFrame(returns)
        
        # Calculate expected returns and covariance
        mu = returns_df.mean() * 252
        cov = returns_df.cov() * 252
        
        # Optimize weights
        weights = self._optimize_portfolio(mu, cov)
        
        # Calculate target positions
        signals = {}
        for i, ticker in enumerate(returns_df.columns):
            target_value = cash * weights[i]
            current_price = price_data[ticker]['Close'].iloc[-1]
            target_shares = int(target_value / current_price)
            signals[ticker] = target_shares - positions[ticker].shares
        
        return signals if any(signals.values()) else None
```

### Pairs Trading

```python
@StrategyFactory.register("pairs_trading")
class PairsTradingStrategy(StrategyBase):
    def __init__(self, ticker1, ticker2, lookback=30, entry_z=2.0):
        self.ticker1 = ticker1
        self.ticker2 = ticker2
        self.lookback_period = lookback
        self.entry_z = entry_z
    
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        df1 = price_data[self.ticker1]
        df2 = price_data[self.ticker2]
        
        # Calculate spread
        spread = df1['Close'] / df2['Close']
        mean = spread.rolling(window=self.lookback_period).mean()
        std = spread.rolling(window=self.lookback_period).std()
        z_score = (spread - mean) / std
        
        current_z = z_score.iloc[-1]
        signals = {}
        
        if current_z > self.entry_z:
            # Short ticker1, long ticker2
            signals[self.ticker1] = -int(cash * 0.5 / df1['Close'].iloc[-1])
            signals[self.ticker2] = int(cash * 0.5 / df2['Close'].iloc[-1])
        
        return signals if signals else None
```

## 🤖 Machine Learning Integration

### ML-Based Strategy

```python
@StrategyFactory.register("ml_strategy")
class MLStrategy(StrategyBase):
    def __init__(self, model_path):
        self.model = joblib.load(model_path)
        self.lookback_period = 30
    
    def _extract_features(self, df):
        features = {
            'sma_5': df['Close'].rolling(5).mean().iloc[-1],
            'sma_20': df['Close'].rolling(20).mean().iloc[-1],
            'rsi': self._calculate_rsi(df['Close']).iloc[-1],
            'return_1d': df['Close'].pct_change(1).iloc[-1]
        }
        return pd.DataFrame([features])
    
    def generate_signals(self, price_data, current_date, positions, cash, **kwargs):
        ticker = list(positions.keys())[0]
        features = self._extract_features(price_data[ticker])
        
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0]
        
        if prediction == 1 and probability[1] > 0.7:
            shares = int(cash / price_data[ticker]['Close'].iloc[-1])
            return {ticker: shares}
        elif prediction == 0 and probability[0] > 0.7:
            return {ticker: -positions[ticker].shares}
        
        return None
```

## ⚡ Performance Optimization

### Vectorized Operations

```python
# Fast: Vectorized
signals = (df['Close'] > df['SMA']).astype(int)

# Slow: Loop
signals = {}
for i in range(len(df)):
    if df['Close'].iloc[i] > df['SMA'].iloc[i]:
        signals[i] = 1
```

### Parallel Backtesting

```python
from multiprocessing import Pool

def run_backtest(params):
    strategy_name, ticker, start, end = params
    # Run backtest
    return final_net_worth

params = list(itertools.product(strategies, tickers, ['2023-01-01'], ['2024-01-01']))

with Pool(processes=4) as pool:
    results = pool.map(run_backtest, params)
```

## 🔴 Live Trading Deployment

### Production Setup

```python
class LiveTradingSystem:
    def __init__(self, portfolio, broker_api, strategy):
        self.portfolio = portfolio
        self.broker_api = broker_api
        self.strategy = strategy
        self.executor = LiveExecutor(portfolio, broker_api)
    
    def run(self):
        while self._is_market_open():
            try:
                # Get market data
                market_data = self._fetch_live_data()
                
                # Generate signals
                signals = self.strategy.generate_signals(...)
                
                # Execute trades
                if signals:
                    for ticker, shares in signals.items():
                        order = Order(ticker=ticker, ...)
                        self.executor.submit_order(order)
                
                # Process fills
                self.executor.step(datetime.now())
                
                time.sleep(60)
            except Exception as e:
                logging.error(f"Error: {e}")
                time.sleep(60)
```

## 🔧 Custom Executors

### Slippage Model

```python
class CustomSlippageExecutor(BaseExecutor):
    def _calculate_slippage(self, ticker, quantity, price):
        avg_volume = self.market_data.data[ticker]['Volume'].rolling(20).mean().iloc[-1]
        order_size_pct = quantity / avg_volume
        
        if order_size_pct < 0.01:
            slippage = 0.0005
        elif order_size_pct < 0.05:
            slippage = 0.001
        else:
            slippage = 0.005
        
        return price * slippage
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Strategy Development](./05-strategies.md)
- [Execution Engines](./06-executors.md)
- [Analytics & Performance](./09-analytics.md)
- [Examples & Tutorials](./12-examples.md)

---

**Code References**:
- [`strategies/multi_asset/`](../strategies/multi_asset/)
- [`strategies/derivatives/`](../strategies/derivatives/)
- [`executors/`](../executors/)
