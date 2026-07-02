import numpy as np
import pandas as pd
import pytest

from core.universe import ListUniverse
from research.report import write_distribution_report
from research.sweep import sweep_universe
from strategies.buy_n_hold import BuyAndHold
from strategies.momentum import Momentum

_DATES = pd.date_range("2020-01-01", periods=200, freq="B")


def _series(rate: float) -> pd.Series:
    return pd.Series(100 * (rate ** np.arange(len(_DATES))), index=_DATES)


def _loader(rates):
    def load(ticker: str) -> pd.DataFrame:
        return pd.DataFrame({ticker: _series(rates[ticker])}, index=_DATES)
    return load


def _benchmark() -> pd.DataFrame:
    return pd.DataFrame({"SPY": _series(1.0003)}, index=_DATES)


def test_sweep_returns_per_name_metrics():
    rates = {"FAST": 1.0015, "SLOW": 1.0004, "FLATISH": 1.0001}
    metrics = sweep_universe(
        Momentum(3, 10), ListUniverse(list(rates)), _benchmark(),
        "2020-01-01", "2020-12-31", price_loader=_loader(rates), min_days=30,
    )
    assert set(metrics.columns) >= {"alpha", "beta", "sharpe", "total_return",
                                    "benchmark_return", "excess_return"}
    assert len(metrics) == 3
    # sorted by alpha descending
    assert metrics["alpha"].is_monotonic_decreasing


def test_sweep_rejects_basket_strategy():
    with pytest.raises(ValueError):
        sweep_universe(BuyAndHold(), ListUniverse(["AAA"]), _benchmark(),
                       "2020-01-01", "2020-12-31", price_loader=_loader({"AAA": 1.001}))


def test_distribution_report_writes_artifacts(tmp_path):
    rates = {"FAST": 1.0015, "SLOW": 1.0004}
    metrics = sweep_universe(
        Momentum(3, 10), ListUniverse(list(rates)), _benchmark(),
        "2020-01-01", "2020-12-31", price_loader=_loader(rates), min_days=30,
    )
    paths = write_distribution_report(metrics, str(tmp_path), "momentum", caveat="test caveat")
    assert (tmp_path / "per_name_metrics.csv").exists()
    assert (tmp_path / "distribution_summary.csv").exists()
    assert (tmp_path / "alpha_beta_distribution.html").stat().st_size > 1000
