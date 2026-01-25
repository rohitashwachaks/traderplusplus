# Analytics & Performance

Guide to performance evaluation, metrics calculation, and result analysis.

## 📋 Overview

Trader++ provides comprehensive analytics:
- **Performance Metrics**: Sharpe, alpha, beta, drawdown
- **Benchmark Comparison**: Compare against market indices
- **Risk Analysis**: Volatility, drawdown, win rate
- **Visualization**: Equity curves, drawdown charts

**Location**: [`analytics/`](../analytics/)

## 📊 PerformanceEvaluator

**Location**: [`analytics/performance_evaluator.py`](../analytics/performance_evaluator.py)

Main class for computing performance metrics.

### Usage

```python
from analytics.performance_evaluator import PerformanceEvaluator

equity_curve = backtester.get_equity_curve()

evaluator = PerformanceEvaluator(
    portfolio_curve=equity_curve['net_worth'],
    benchmark_curve=equity_curve['benchmark'],
    risk_free_rate=0.04  # 4% annual
)

metrics = evaluator.compute_metrics()
print(evaluator.summary())
```

### Metrics Returned

```python
{
    'portfolio_return': 0.1875,      # Total return
    'benchmark_return': 0.1234,      # Benchmark return
    'active_return': 0.0641,         # Excess return
    'win': 0.5476,                   # Win rate
    'cagr': 0.1823,                  # Annual growth rate
    'volatility': 0.2145,            # Annual volatility
    'sharpe': 0.8495,                # Sharpe ratio
    'alpha': 0.0234,                 # Jensen's alpha
    'beta': 1.0823,                  # Market beta
    'max_drawdown': -0.1234          # Maximum drawdown
}
```

## 📈 Performance Metrics

### Return Metrics

**Total Return**: Percentage gain/loss
```python
total_return = (final_value / initial_value) - 1
```

**CAGR**: Annualized return
```python
cagr = daily_returns.mean() * 252
```

**Active Return**: Excess over benchmark
```python
active_return = portfolio_return - benchmark_return
```

### Risk Metrics

**Volatility**: Annualized standard deviation
```python
volatility = daily_returns.std() * np.sqrt(252)
```

**Maximum Drawdown**: Largest peak-to-trough decline
```python
max_drawdown = ((equity_curve - equity_curve.cummax()) / equity_curve.cummax()).min()
```

**Beta**: Market sensitivity
```python
beta = cov(portfolio_returns, benchmark_returns) / var(benchmark_returns)
```

### Risk-Adjusted Metrics

**Sharpe Ratio**: Return per unit of risk
```python
sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
```

**Interpretation**:
- `> 1.0` = Good
- `> 2.0` = Very good
- `> 3.0` = Excellent

**Alpha**: Excess return after risk adjustment
```python
alpha = portfolio_return - (risk_free_rate + beta * (benchmark_return - risk_free_rate))
```

### Trading Metrics

**Win Rate**: Percentage of profitable days
```python
win_rate = (daily_returns > 0).mean()
```

## 📊 Visualization

### Equity Curve

```python
from core.visualizer import plotly_equity_vs_benchmark

plotly_equity_vs_benchmark(
    equity_curve['net_worth'],
    equity_curve['benchmark'],
    trade_logs=trade_log
)
```

### Drawdown Chart

```python
from core.visualizer import plot_drawdown

plot_drawdown(equity_curve['net_worth'])
```

## 🎯 Practical Examples

### Basic Analysis

```python
evaluator = PerformanceEvaluator(
    equity_curve['net_worth'],
    equity_curve['benchmark']
)

metrics = evaluator.compute_metrics()
print(f"Sharpe Ratio: {metrics['sharpe']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
```

### Compare Strategies

```python
strategies = ['momentum', 'buy_n_hold']
results = {}

for strategy in strategies:
    # Run backtest
    backtester.run(...)
    evaluator = PerformanceEvaluator(...)
    results[strategy] = evaluator.compute_metrics()

comparison = pd.DataFrame(results).T
print(comparison)
```

## 📉 Interpreting Results

### Good Strategy Characteristics
- Sharpe Ratio > 1.0
- Max Drawdown < 20%
- Win Rate > 50%
- Positive Alpha
- Beta 0.8-1.2

### Warning Signs
- Sharpe Ratio < 0.5
- Max Drawdown > 30%
- Win Rate < 45%
- Negative Alpha

## 💡 Best Practices

1. **Always Compare to Benchmark**: Account for market conditions
2. **Use Risk-Free Rate**: Include current T-bill rate
3. **Analyze Multiple Periods**: Test across different market conditions
4. **Consider Transaction Costs**: Account for slippage and fees
5. **Export Results**: Save for further analysis

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Strategy Development](./05-strategies.md)
- [Examples & Tutorials](./12-examples.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`analytics/performance_evaluator.py`](../analytics/performance_evaluator.py)
- [`analytics/performance.py`](../analytics/performance.py)
- [`core/visualizer.py`](../core/visualizer.py)
