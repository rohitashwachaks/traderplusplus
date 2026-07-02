import numpy as np
import pandas as pd

from core.context import DataContext, build_context
from core.fundamentals import annual_eps_series
from core.universe import ListUniverse
from strategies.long_short_pe import LongShortPE


def test_annual_eps_keeps_annual_and_as_first_filed():
    records = [
        # FY2020 first reported 2021-02-15 at 5.0
        {"start": "2020-01-01", "end": "2020-12-31", "filed": "2021-02-15", "val": 5.0, "fp": "FY"},
        # a later restatement of FY2020 — must be IGNORED (we keep as-first-filed)
        {"start": "2020-01-01", "end": "2020-12-31", "filed": "2022-03-01", "val": 4.0, "fp": "FY"},
        # a quarter — must be EXCLUDED (not a full year)
        {"start": "2021-01-01", "end": "2021-03-31", "filed": "2021-04-20", "val": 1.2, "fp": "Q1"},
        # FY2021 reported 2022-02-15 at 6.0
        {"start": "2021-01-01", "end": "2021-12-31", "filed": "2022-02-15", "val": 6.0, "fp": "FY"},
    ]
    series = annual_eps_series(records)
    assert list(series.values) == [5.0, 6.0]                      # restatement & quarter dropped
    assert list(series.index) == [pd.Timestamp("2021-02-15"), pd.Timestamp("2022-02-15")]


def test_eps_panel_is_point_in_time(monkeypatch):
    """EPS is invisible until its filing date: before the filing the panel is NaN, after it the
    value appears (forward-filled). Truncating the future can't change that — no look-ahead."""
    dates = pd.date_range("2021-01-01", "2021-06-30", freq="B")
    price = pd.DataFrame(100.0, index=dates, columns=["A", "B"])
    eps_panel = pd.DataFrame({"A": [5.0], "B": [8.0]}, index=[pd.Timestamp("2021-02-15")])

    class FakePrice:
        def load(self, tickers, start, end, **opts):
            return price[list(tickers)]

    class FakeEps:
        def load(self, tickers, start, end, **opts):
            return eps_panel[list(tickers)]

    monkeypatch.setattr("core.context._sources.get_source",
                        lambda name: FakeEps() if name == "eps" else FakePrice())

    ctx = build_context(ListUniverse(["A", "B"]), "2021-01-01", "2021-06-30", panels=("price", "eps"))
    eps = ctx.panel("eps")
    assert eps.loc[pd.Timestamp("2021-01-15")].isna().all()       # before filing → unknown
    assert eps.loc[pd.Timestamp("2021-03-01"), "A"] == 5.0        # after filing → known, ffilled


def _ls_pe_context():
    dates = pd.date_range("2022-01-03", periods=5, freq="B")
    tickers = ["T1", "T2", "T3", "T4", "T5", "T6"]
    price = pd.DataFrame(100.0, index=dates, columns=tickers)
    eps = pd.DataFrame({t: float(i + 1) for i, t in enumerate(tickers)}, index=dates)  # P/E = 100/eps
    members = pd.DataFrame(True, index=dates, columns=tickers)
    return DataContext(panels={"price": price, "members": members, "eps": eps},
                       meta=pd.DataFrame(index=tickers))


def test_ls_pe_is_dollar_neutral_long_cheap_short_rich():
    weights = LongShortPE(n=2).weights(_ls_pe_context()).iloc[-1]
    assert abs(weights.sum()) < 1e-9                              # market-neutral
    # P/E = 100/eps → cheapest (lowest P/E) are highest-eps T6,T5 (long); richest are T1,T2 (short)
    assert weights["T6"] > 0 and weights["T5"] > 0
    assert weights["T1"] < 0 and weights["T2"] < 0
    assert weights["T3"] == 0 and weights["T4"] == 0


def test_ls_pe_needs_a_full_book():
    """With fewer than 2*n valid P/Es, no book is formed (weights all zero)."""
    ctx = _ls_pe_context()
    eps = ctx.panel("eps").copy()
    eps.iloc[:, 3:] = np.nan                                      # only 3 valid names, need 2*2=4
    ctx = DataContext(panels={"price": ctx.price, "members": ctx.members, "eps": eps}, meta=ctx.meta)
    assert (LongShortPE(n=2).weights(ctx) == 0.0).all().all()
