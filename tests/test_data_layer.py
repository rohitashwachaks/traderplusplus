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


def test_to_price_panel_outer_keeps_union_with_nan():
    from core.price_panel import to_price_panel
    dates = pd.date_range("2020-01-01", periods=5, freq="B", tz="UTC")

    def d(vals):
        return pd.DataFrame({"Close": vals}, index=dates)

    panel = to_price_panel({"A": d([1, 2, 3, 4, 5.0]), "B": d([np.nan, np.nan, 3, 4, 5.0])}, how="outer")
    assert len(panel) == 5                         # union of dates, nothing dropped
    assert panel["B"].isna().sum() == 2            # B's pre-listing gap preserved as NaN


def test_build_context_membership_is_tradable_mask(monkeypatch):
    dates = pd.date_range("2020-01-01", periods=5, freq="B")
    price = pd.DataFrame(
        {"A": [1, 2, 3, 4, 5.0], "B": [np.nan, np.nan, 3, 4, 5.0], "DEAD": [np.nan] * 5},
        index=dates,
    )

    class FakeSource:
        def load(self, tickers, start, end, **opts):
            return price[list(tickers)]

    monkeypatch.setattr("core.context._sources.get_source", lambda name: FakeSource())
    ctx = build_context(ListUniverse(["A", "B", "DEAD"]), "2020-01-01", "2020-02-01")

    assert "DEAD" not in ctx.price.columns         # all-NaN name dropped (logged)
    assert ctx.members["A"].all()
    assert not ctx.members["B"].iloc[0]            # B not tradable before it has a price
    assert ctx.members["B"].iloc[-1]               # tradable once data appears
