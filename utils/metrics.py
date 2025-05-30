import numpy as np
import pandas as pd


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.01) -> float:
    """Annualized Sharpe Ratio based on daily returns."""
    excess_returns = returns - (risk_free_rate / 252)
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Compute max drawdown as the maximum loss from peak equity."""
    cumulative_max = equity_curve.cummax()
    drawdown = (equity_curve - cumulative_max) / cumulative_max
    return drawdown.min()


def calculate_cagr(equity_curve: pd.Series) -> float:
    """Compute Compound Annual Growth Rate (CAGR)."""
    total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    return (1 + total_return) ** (365.0 / total_days) - 1


def win_rate(trades_df: pd.DataFrame) -> float:
    """Compute the win rate of executed trades."""
    if 'pnl' not in trades_df.columns or trades_df.empty:
        return 0.0
    wins = trades_df[trades_df['pnl'] > 0].shape[0]
    total = trades_df[trades_df['type'] == 'SELL'].shape[0]
    return wins / total if total > 0 else 0.0


def summarize_metrics(equity_curve: pd.Series, trades_df: pd.DataFrame, name: str = ""):
    """Print a basic summary report."""
    returns = equity_curve.pct_change().dropna()

    print(f"\n📊 Performance Summary: {name}")
    print("-" * 40)
    print(f"Sharpe Ratio:       {calculate_sharpe_ratio(returns):.2f}")
    print(f"Max Drawdown:       {calculate_max_drawdown(equity_curve):.2%}")
    print(f"CAGR:               {calculate_cagr(equity_curve):.2%}")
    print(f"Win Rate:           {win_rate(trades_df):.2%}")