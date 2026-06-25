import numpy as np
import pandas as pd
import pytest

from core.context import DataContext, build_context
from core.universe import SP500, ListUniverse


def _panel(cols):
    dates = pd.date_range("2022-01-01", periods=30, freq="B")
    return pd.DataFrame({c: 100 + np.arange(30) for c in cols}, index=dates, dtype=float)


def test_from_prices_defaults_to_all_in_membership():
    prices = _panel(["AAPL", "MSFT"])
    ctx = DataContext.from_prices(prices)
    assert ctx.members.all().all()              # all names in-universe by default
    assert list(ctx.price.columns) == ["AAPL", "MSFT"]


def test_panel_lookup_raises_for_unknown():
    ctx = DataContext.from_prices(_panel(["AAPL"]))
    with pytest.raises(KeyError):
        ctx.panel("pe")                          # no source registered for it here


def test_list_universe_normalizes_symbols():
    universe = ListUniverse(["brk.b", " aapl "])
    assert universe.tickers() == ["BRK-B", "AAPL"]  # dots->dashes (yahoo), upper, trimmed


def test_build_context_assembles_and_aligns(monkeypatch):
    prices = _panel(["AAPL", "MSFT"])

    class FakePriceSource:
        def load(self, tickers, start, end, **opts):
            return prices[list(tickers)]

    monkeypatch.setattr("core.context._sources.get_source", lambda name: FakePriceSource())

    ctx = build_context(ListUniverse(["AAPL", "MSFT"]), "2022-01-01", "2022-03-01")
    assert list(ctx.price.columns) == ["AAPL", "MSFT"]
    assert ctx.members.shape == ctx.price.shape and ctx.members.all().all()


def test_build_context_requires_price_panel():
    with pytest.raises(ValueError):
        build_context(ListUniverse(["AAPL"]), "2022-01-01", "2022-03-01", panels=("pe",))


def test_sp500_reads_pasted_csv(tmp_path):
    csv = tmp_path / "sp500.csv"
    csv.write_text(
        "Symbol,Security,GICS Sector,GICS Sub-Industry\n"
        "AAPL,Apple Inc.,Information Technology,Tech Hardware\n"
        "BRK.B,Berkshire Hathaway,Financials,Multi-Sector Holdings\n"
    )
    universe = SP500(path=str(csv))
    assert universe.tickers() == ["AAPL", "BRK-B"]              # normalized + sorted
    assert universe.meta().loc["AAPL", "sector"] == "Information Technology"
    assert universe.biased and universe.stamp() is not None


def test_sp500_missing_file_raises_clearly():
    with pytest.raises(RuntimeError, match="snapshot not found"):
        SP500(path="/no/such/sp500.csv").tickers()
