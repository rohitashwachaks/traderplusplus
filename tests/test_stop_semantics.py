"""Stop-order fidelity: intraday touch detection, High-trailing, and — the regression that
motivated all of it — a stop exit that fires mid-period instead of waiting for the next
scheduled rebalance/reconstitution."""
import numpy as np
import pandas as pd
import pytest

from core.context import DataContext
from engine.runner import run
from guardrails.stop_loss import StopLoss
from strategies.base import TargetWeightStrategy


def _frame(values, col="AAPL", start="2022-01-03"):
    dates = pd.date_range(start, periods=len(values), freq="B")
    return pd.DataFrame({col: values}, index=dates, dtype=float)


def _hold_weights(prices):
    return pd.DataFrame(1.0, index=prices.index, columns=prices.columns)


def test_intraday_low_touch_triggers_even_when_close_recovers():
    """Closes never breach the stop, but one day's Low touches it — a real stop order
    would have fired, so ours must too (exit at that day's close)."""
    close = _frame([100, 104, 108, 110, 109, 108, 108, 108])
    high = close + 1.0
    low = close - 1.0
    low.iloc[5] = 100.0   # peak high = 110(day3)+1=111 → 7% level 103.2; low 100 touches it

    adjusted = StopLoss(0.07, trailing=True).apply(
        close, _hold_weights(close), high=high, low=low)["AAPL"]

    assert (adjusted.iloc[:5] == 1.0).all()
    assert (adjusted.iloc[5:] == 0.0).all(), "intraday touch must stop out on the touch day"


def test_trailing_reference_uses_intraday_high():
    """The trail rides the intraday High, not the close — a close-only trail would sit
    lower and never fire here."""
    close = _frame([100, 101, 102, 102, 97, 97])
    high = close.copy()
    high.iloc[3] = 110.0   # intraday spike: level becomes 110 * 0.93 = 102.3
    low = close.copy()

    adjusted = StopLoss(0.07, trailing=True).apply(
        close, _hold_weights(close), high=high, low=low)["AAPL"]

    # Day 4: low 97 <= 102.3 → stopped. Off closes alone (peak 102 → 94.9) it would hold.
    assert adjusted.iloc[3] == 1.0
    assert (adjusted.iloc[4:] == 0.0).all()


def test_levels_diagnostic_exposes_the_stop_line():
    close = _frame([100, 110, 108, 104, 104])
    guard = StopLoss(0.05, trailing=True)
    guard.apply(close, _hold_weights(close), high=close, low=close)

    levels = guard.levels_["AAPL"]
    assert np.isnan(levels.iloc[0])                     # entry day: no level yet
    assert levels.iloc[1] == pytest.approx(95.0)        # level as of the open (entry ref 100)
    assert levels.iloc[2] == pytest.approx(104.5)       # trailed to the 110 peak
    assert levels.iloc[3] == pytest.approx(104.5)       # breach day still shows the line
    assert np.isnan(levels.iloc[4])                     # out → no active level


def test_cooldown_reentry_rides_the_recovery_and_rearms_the_stop():
    """A slow signal that never went flat used to latch the name out through a whole
    recovery. With ``reentry_days`` the stop steps back in and trails from the new close."""
    close = _frame([100, 110, 100, 101, 102, 103, 120, 140, 160, 180])
    guard = StopLoss(0.07, trailing=True, reentry_days=3)
    adjusted = guard.apply(close, _hold_weights(close), high=close, low=close)["AAPL"]

    # Peak 110 → level 102.3; day 2's 100 breaches → out that day.
    assert adjusted.iloc[2] == 0.0
    assert (adjusted.iloc[3:5] == 0.0).all()            # cooling down
    assert (adjusted.iloc[5:] == 1.0).all()             # 3 days served → rides the recovery
    # The stop re-armed from the re-entry close (103), not the stale pre-crash peak.
    assert guard.levels_["AAPL"].iloc[6] == pytest.approx(103 * 0.93)


def test_no_reentry_by_default_when_signal_never_goes_flat():
    close = _frame([100, 110, 100, 101, 102, 103, 120, 140, 160, 180])
    adjusted = StopLoss(0.07, trailing=True).apply(
        close, _hold_weights(close), high=close, low=close)["AAPL"]
    assert (adjusted.iloc[2:] == 0.0).all()             # latched out for good (documented)


def test_reentry_days_must_be_positive():
    with pytest.raises(ValueError, match="reentry_days"):
        StopLoss(0.05, reentry_days=0)


class MonthlyHold(TargetWeightStrategy):
    """Fully hold one name, reconstituted/rebalanced monthly — the cadence that used to
    swallow mid-month stop exits."""

    name = "monthly_hold"
    rebalance_freq = "M"
    reconstitution_freq = "M"

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        return pd.DataFrame(1.0, index=ctx.price.index, columns=ctx.price.columns)


def test_stop_exit_fires_mid_month_not_at_the_next_rebalance():
    """The user-visible bug: 7% trailing stop, but the exit slid to the next monthly
    rebalance while the position kept crashing. The exit must land on the breach day's
    close and the equity must be flat (cash) from that day on."""
    dates = pd.date_range("2022-01-03", periods=60, freq="B")   # ~3 months
    values = np.concatenate([
        np.linspace(100, 120, 25),     # run-up through January into February
        [102.0],                       # day 25 (~Feb 7): -15% crash through the 7% stop
        np.linspace(96, 60, 34),       # keeps falling to month-end and beyond
    ])
    prices = pd.DataFrame({"AAPL": values}, index=dates)
    benchmark = pd.DataFrame({"SPY": np.linspace(100, 110, 60)}, index=dates)

    res = run(MonthlyHold(), DataContext.from_prices(prices), benchmark,
              guardrails=[StopLoss(0.07, trailing=True)])
    equity = res.prices["monthly_hold"]

    # Out at the crash day's close → equity never moves again (all cash), even though the
    # price keeps falling for weeks before the next scheduled monthly rebalance.
    post_crash = equity.iloc[26:]
    assert post_crash.max() - post_crash.min() < 1e-6, \
        "equity moved after the stop-out — the exit waited for the scheduled rebalance"
    # And the damage is the crash-day loss, not the ride to the bottom (60/120 = -50%).
    assert equity.iloc[-1] / equity.iloc[:26].max() > 0.80
