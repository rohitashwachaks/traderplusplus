import pandas as pd
from typing import Dict


def evaluate_portfolio_performance(trade_log: pd.DataFrame, benchmark_data: pd.DataFrame) -> Dict[str, float]:
    """
    Evaluate portfolio performance using trade logs and benchmark returns.

    :param trade_log: DataFrame of trade history with 'date' and 'cash_remaining'
    :param benchmark_data: DataFrame with 'Close' prices indexed by date
    :return: Dictionary with performance metrics like sharpe and alpha
    """
    if trade_log.empty or benchmark_data.empty:
        return {"sharpe": float('nan'), "alpha": float('nan')}

    equity_curve = trade_log.groupby('date')['cash_remaining'].last().fillna(method='ffill')
    returns = equity_curve.pct_change().dropna()

    benchmark_returns = benchmark_data['Close'].pct_change().dropna()
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    aligned.columns = ['portfolio', 'benchmark']

    excess_returns = aligned['portfolio'] - aligned['benchmark']
    alpha = excess_returns.mean() * 252
    sharpe = aligned['portfolio'].mean() / aligned['portfolio'].std() * (252 ** 0.5)

    return {
        "sharpe": round(sharpe, 4),
        "alpha": round(alpha, 4)
    }
