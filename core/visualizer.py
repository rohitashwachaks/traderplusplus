import os
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter

import plotly.graph_objects as go


def _validate_equity_series(equity_curve: pd.Series):
    if not isinstance(equity_curve, pd.Series):
        raise TypeError(f"Expected Series, got {type(equity_curve)}")
    if not pd.api.types.is_numeric_dtype(equity_curve):
        raise ValueError(f"Equity curve must be numeric, got {equity_curve.dtype}")
    if not isinstance(equity_curve.index, pd.DatetimeIndex):
        raise ValueError("Equity curve index must be datetime.")


def _finalize_plot(title: str):
    try:
        plt.tight_layout()
    except RecursionError:
        print("⚠️ Warning: RecursionError in tight_layout. Skipping layout auto-adjust.")
    os.makedirs("./figures", exist_ok=True)
    safe_title = title.lower().replace(" ", "_")
    plt.savefig(f"./figures/{safe_title}.png")
    fig = plt.gcf()
    plt.close()
    return fig


def plot_equity_curve(equity_curve: pd.Series, title: str = "Equity Curve"):
    _validate_equity_series(equity_curve)

    plt.figure(figsize=(10, 4))
    plt.plot(equity_curve, label='Equity', linewidth=2)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    return _finalize_plot(title)


def plot_drawdown(equity_curve: pd.Series, title: str = "Drawdown"):
    _validate_equity_series(equity_curve)

    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max

    plt.figure(figsize=(10, 3))
    plt.fill_between(drawdown.index, drawdown, color='red', alpha=0.5)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    return _finalize_plot(title)


def plot_per_asset_equity(position_history: Dict[str, List[int]],
                          prices: Dict[str, pd.DataFrame],
                          title: str = "Per-Asset Equity Curve"):
    plt.figure(figsize=(12, 6))
    for ticker, shares_series in position_history.items():
        if ticker not in prices:
            continue
        price_series = prices[ticker]['Close'].iloc[-len(shares_series):]
        value_series = pd.Series(shares_series, index=price_series.index) * price_series
        plt.plot(value_series, label=f"{ticker} Value")

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Asset Value ($)")
    plt.grid(True)
    plt.legend()
    return _finalize_plot(title)


def plot_equity_with_trades(equity_curve: pd.Series,
                            trades: pd.DataFrame,
                            title: str = "Equity Curve with Trades"):
    _validate_equity_series(equity_curve)

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 4))
    plt.plot(equity_curve, label='Equity', linewidth=2)

    for _, row in trades.iterrows():
        color = 'green' if row['action'] == 'BUY' else 'red'
        date = pd.to_datetime(row['date'])
        if date in equity_curve.index:
            plt.axvline(date, color=color, linestyle='--', alpha=0.5)
            plt.text(date, equity_curve.max() * 0.95, f"{row['ticker']}", fontsize=8, rotation=90)

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Net Worth")
    plt.grid(True)
    plt.legend()
    return _finalize_plot(title)


def plotly_interactive_equity(equity_curve: pd.Series,
                              trades: pd.DataFrame = None,
                              title: str = "Interactive Equity Curve"):
    _validate_equity_series(equity_curve)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve.values,
        mode='lines',
        name='Net Worth',
        line=dict(width=2)
    ))

    if trades is not None:
        for action in ['BUY', 'SELL']:
            filtered = trades[trades['action'] == action]
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(filtered['date']),
                y=[equity_curve.get(pd.to_datetime(d), None) for d in filtered['date']],
                mode='markers',
                marker=dict(
                    color='green' if action == 'BUY' else 'red',
                    symbol='triangle-up' if action == 'BUY' else 'triangle-down',
                    size=10
                ),
                name=action
            ))

    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Net Worth")
    fig.show()
    return fig


def plot_equity_vs_networth(equity_curve: pd.Series,
                            networth_curve: pd.Series,
                            title: str = "Strategy vs Net Worth"):
    _validate_equity_series(equity_curve)
    _validate_equity_series(networth_curve)

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 5))
    plt.plot(equity_curve, label='Strategy Equity', linewidth=2)
    plt.plot(networth_curve, label='Actual Net Worth', linestyle='--', linewidth=2)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Value ($)")
    plt.grid(True)
    plt.legend()
    return _finalize_plot(title)


def plot_equity_vs_benchmark(
    portfolio_curve: pd.Series,
    benchmark_curve: pd.Series,
    title: str = "Strategy vs Benchmark Equity Curve",
    normalize: bool = True
):
    """
    Plot portfolio equity and benchmark on the same chart for visual comparison.
    If normalize=True, both curves start at 1 for relative performance.
    """
    _validate_equity_series(portfolio_curve)
    _validate_equity_series(benchmark_curve)
    import matplotlib.pyplot as plt
    import pandas as pd
    # Align indices
    common_idx = portfolio_curve.index.intersection(benchmark_curve.index)
    p_curve = portfolio_curve.loc[common_idx]
    b_curve = benchmark_curve.loc[common_idx]
    if normalize:
        p_curve = p_curve / p_curve.iloc[0]
        b_curve = b_curve / b_curve.iloc[0]
    plt.figure(figsize=(12, 5))
    plt.plot(p_curve, label='Strategy', linewidth=2)
    plt.plot(b_curve, label='Benchmark', linestyle='--', linewidth=2)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Normalized Value" if normalize else "Value ($)")
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    return _finalize_plot(title)


def plotly_equity_vs_benchmark(
    portfolio_curve: pd.Series,
    benchmark_curve: pd.Series,
    title: str = "Strategy vs Benchmark Equity Curve",
    normalize: bool = True
):
    """
    Plotly interactive chart for portfolio vs benchmark.
    """
    import plotly.graph_objects as go
    import pandas as pd
    # Align indices
    common_idx = portfolio_curve.index.intersection(benchmark_curve.index)
    p_curve = portfolio_curve.loc[common_idx]
    b_curve = benchmark_curve.loc[common_idx]
    if normalize:
        p_curve = p_curve / p_curve.iloc[0]
        b_curve = b_curve / b_curve.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p_curve.index, y=p_curve, mode='lines', name='Strategy'))
    fig.add_trace(go.Scatter(x=b_curve.index, y=b_curve, mode='lines', name='Benchmark'))
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title='Normalized Value' if normalize else 'Value ($)', template='plotly_white')
    return fig