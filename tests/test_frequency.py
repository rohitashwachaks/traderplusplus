import bt
import numpy as np
import pandas as pd
import pytest

from engine import frequency


def test_normalize_aliases():
    assert frequency.normalize("quarterly") == "Q"
    assert frequency.normalize("Y") == "Y"
    assert frequency.normalize("daily") == "D"
    with pytest.raises(ValueError):
        frequency.normalize("fortnightly")


def test_run_algo_types():
    assert isinstance(frequency.run_algo("Q"), bt.algos.RunQuarterly)
    assert isinstance(frequency.run_algo("Y"), bt.algos.RunYearly)


def _daily_changing_weights():
    dates = pd.date_range("2022-01-01", periods=400, freq="B")
    # A weight that drifts every single day, so resampling has something to freeze.
    w = pd.Series(np.linspace(0.1, 0.9, len(dates)), index=dates)
    return pd.DataFrame({"AAPL": w})


def test_daily_reconstitution_is_identity():
    w = _daily_changing_weights()
    pd.testing.assert_frame_equal(frequency.resample_reconstitution(w, "D"), w)


def test_quarterly_reconstitution_freezes_within_period():
    w = _daily_changing_weights()
    out = frequency.resample_reconstitution(w, "Q")

    period = w.index.to_period("Q")
    # Within each quarter the weight is constant and equals the quarter's first value.
    for _, idx in pd.Series(period, index=w.index).groupby(period).groups.items():
        block = out.loc[idx, "AAPL"]
        assert block.nunique() == 1
        assert block.iloc[0] == w.loc[idx[0], "AAPL"]


def test_reconstitution_no_lookahead():
    """Resampling only forward fills from past boundaries, so truncating the future can't
    change a past value."""
    w = _daily_changing_weights()
    full = frequency.resample_reconstitution(w, "Q")
    t = w.index[250]
    trunc = frequency.resample_reconstitution(w.loc[:t], "Q")
    assert full.loc[t, "AAPL"] == trunc.loc[t, "AAPL"]
