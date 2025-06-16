"""
PerformanceEvaluator: Evaluate portfolio performance against a benchmark.
Clean, stateless, and extensible. Accepts equity curves as pandas Series/DataFrames.
"""
from typing import Optional, Dict
import pandas as pd
import numpy as np


class PerformanceEvaluator:
    """
    Evaluates portfolio performance relative to a benchmark.
    Usage:
        evaluator = PerformanceEvaluator(equity_curve, benchmark_curve)
        metrics = evaluator.compute_metrics()
    """
    def __init__(self, 
                 portfolio_curve: pd.Series, 
                 benchmark_curve: pd.Series,
                 risk_free_rate: float = 0.0):
        """
        Args:
            portfolio_curve (pd.Series): Portfolio net worth indexed by date.
            benchmark_curve (pd.Series): Benchmark value/indexed by date.
            risk_free_rate (float): Annualized risk-free rate (as decimal).
        """
        self.portfolio_curve = portfolio_curve#.sort_index()
        self.benchmark_curve = benchmark_curve#.sort_index()
        self.risk_free_rate = risk_free_rate
        # self._align_curves()

    # def _align_curves(self):
    #     # Align curves to common dates
    #     common_idx = self.portfolio_curve.index.intersection(self.benchmark_curve.index)
    #     self.portfolio_curve = self.portfolio_curve.loc[common_idx]
    #     self.benchmark_curve = self.benchmark_curve.loc[common_idx]

    def compute_metrics(self) -> Dict[str, float]:
        """
        Compute absolute and relative performance metrics.
        Returns:
            Dict[str, float]: Metrics including return, volatility, Sharpe, alpha, beta, etc.
        """
        port_ret = self.portfolio_curve.pct_change().dropna()
        bench_ret = self.benchmark_curve.pct_change().dropna()
        # Align returns
        port_ret, bench_ret = port_ret.align(bench_ret, join='inner')

        # Defensive checks
        if len(port_ret) < 2 or len(bench_ret) < 2:
            print(f"[WARN] Not enough overlapping data for regression. Portfolio returns: {len(port_ret)}, Benchmark returns: {len(bench_ret)}")
            return {
                'portfolio_return': np.nan,
                'benchmark_return': np.nan,
                'active_return': np.nan,
                'win': np.nan,
                'cagr': np.nan,
                'volatility': np.nan,
                'sharpe': np.nan,
                'alpha': np.nan,
                'beta': np.nan,
                'max_drawdown': np.nan
            }
        excess_ret = port_ret - self.risk_free_rate/252
        excess_bench = bench_ret - self.risk_free_rate/252

        metrics = {}
        metrics['portfolio_return'] = (self.portfolio_curve.iloc[-1] / self.portfolio_curve.iloc[0]) - 1
        metrics['benchmark_return'] = (self.benchmark_curve.iloc[-1] / self.benchmark_curve.iloc[0]) - 1
        metrics['active_return'] = metrics['portfolio_return'] - metrics['benchmark_return']
        metrics['win'] = (port_ret > 0).mean()
        metrics['cagr'] = port_ret.mean() * 252
        metrics['volatility'] = port_ret.std() * np.sqrt(252)
        metrics['sharpe'] = excess_ret.mean() / (port_ret.std() + 1e-9) * np.sqrt(252)

        # Alpha/Beta via linear regression
        try:
            X = np.vstack([np.ones(len(excess_bench)), excess_bench.values]).T
            alpha, beta = np.linalg.lstsq(X, excess_ret.values, rcond=None)[0]
            metrics['alpha'] = alpha * 252  # annualized
            metrics['beta'] = beta
        except Exception as e:
            print(f"[WARN] Could not compute alpha/beta: {e}")
            metrics['alpha'] = np.nan
            metrics['beta'] = np.nan

        # Max drawdown
        roll_max = self.portfolio_curve.cummax()
        drawdown = (self.portfolio_curve - roll_max) / roll_max
        metrics['max_drawdown'] = drawdown.min()

        return metrics

    def summary(self, as_str: bool = True) -> str | dict[str, float]:
        metrics = self.compute_metrics()
        if as_str:
            return '\n'.join(f"{k}: {v:.4f}" for k, v in metrics.items())
        return metrics
