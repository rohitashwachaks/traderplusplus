import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def rising_prices():
    """A smooth upward price panel — deterministic, no network."""
    dates = pd.date_range("2022-01-01", periods=120, freq="B")
    aapl = pd.Series(100 * (1.001 ** np.arange(len(dates))), index=dates)
    msft = pd.Series(50 * (1.0008 ** np.arange(len(dates))), index=dates)
    return pd.DataFrame({"AAPL": aapl, "MSFT": msft})


@pytest.fixture
def choppy_prices():
    """A panel with a real trend reversal, so momentum actually flips in and out."""
    dates = pd.date_range("2022-01-01", periods=120, freq="B")
    t = np.arange(len(dates))
    wave = 100 + 20 * np.sin(t / 8.0)  # oscillates → crossovers happen
    return pd.DataFrame({"AAPL": pd.Series(wave, index=dates)})
