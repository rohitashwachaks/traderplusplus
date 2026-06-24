import pandas as pd

from brokers.base import Broker
from engine.paper import Order, build_plan, execute_plan


class FakeBroker(Broker):
    def __init__(self, equity, positions):
        self._equity = equity
        self._positions = positions
        self.submitted = []

    def equity(self):
        return self._equity

    def positions(self):
        return dict(self._positions)

    def submit(self, ticker, qty, side):
        self.submitted.append((side, qty, ticker))


def test_build_plan_sizes_and_sells_first():
    target = pd.Series({"AAPL": 0.5, "MSFT": 0.5})
    prices = pd.Series({"AAPL": 100.0, "MSFT": 50.0})
    plan = build_plan(target, prices, positions={"AAPL": 0, "MSFT": 200}, equity=10_000)

    by = {o.ticker: o for o in plan}
    assert by["AAPL"].side == "buy" and by["AAPL"].qty == 50      # floor(0.5*10000/100)
    assert by["MSFT"].side == "sell" and by["MSFT"].qty == 100    # 200 held → target 100
    assert plan[0].side == "sell"                                 # sells before buys


def test_build_plan_closes_dropped_ticker():
    target = pd.Series({"AAPL": 1.0})
    prices = pd.Series({"AAPL": 100.0, "MSFT": 50.0})
    plan = build_plan(target, prices, positions={"MSFT": 10}, equity=10_000)

    by = {o.ticker: o for o in plan}
    assert by["MSFT"].side == "sell" and by["MSFT"].qty == 10 and by["MSFT"].target_shares == 0
    assert by["AAPL"].side == "buy" and by["AAPL"].qty == 100


def test_build_plan_skips_subshare_delta():
    target = pd.Series({"AAPL": 0.5})
    prices = pd.Series({"AAPL": 100.0})
    # target floor(0.5*10000/100) = 50 == current → nothing to do
    assert build_plan(target, prices, positions={"AAPL": 50}, equity=10_000) == []


def test_execute_plan_submits_each_order():
    fake = FakeBroker(10_000, {})
    orders = [Order("MSFT", "sell", 3, 0.0, 3, 0), Order("AAPL", "buy", 5, 0.5, 0, 5)]
    execute_plan(fake, orders)
    assert fake.submitted == [("sell", 3, "MSFT"), ("buy", 5, "AAPL")]
