import logging

import numpy as np
import pandas as pd

from guardrails.base import Guardrail, register

log = logging.getLogger("traderplusplus")


@register("stop_loss")
class StopLoss(Guardrail):
    """Force a ticker to cash after it falls ``pct`` from its reference price.

    Models a resting stop order as faithfully as daily bars allow:

    - the reference **trails the intraday high** (``trailing=True``) or stays at the entry
      close (``trailing=False``);
    - the stop **triggers the day the intraday low touches the level** — not only when a
      close crosses it, so a crash *through* the level is caught the day it happens;
    - the exit **fills at that same day's close** and trades immediately, regardless of the
      strategy's rebalance/reconstitution cadence (the engine guarantees this).

    Fill realism, stamped honestly: ``bt`` can only fill at closes. On a crash day the
    close is below the stop level, so the booked exit is *worse* than a real stop order
    (conservative). On a touch-and-recover day the booked close is *better* than the stop
    fill (optimistic). The breach test uses the level as of the day's open (yesterday's
    trail); a same-day new high does not tighten the stop that already fired.

    Without ``high``/``low`` panels (sweeps, close-only tests) it degrades to close-based
    trailing and detection, with a logged notice.

    After a stop-out the ticker is latched out. Release, whichever comes first:

    - the strategy itself goes flat on the name and later re-enters (always); or
    - ``reentry_days`` trading days pass and the strategy still wants the name — then
      re-enter at that day's close, with the stop **re-armed from the re-entry price**.

    ``reentry_days=None`` (default) is signal-only release. That is safe against day-after
    thrashing but can sit out a whole recovery when a slow signal (e.g. an SMA crossover)
    never went flat — for momentum-style strategies a small cooldown is usually what you
    want. The cost is symmetric and disclosed: in a persistent decline the cooldown re-buys
    a falling name once every ``reentry_days``.

    Freed weight goes to cash; it is not redistributed. ``levels_`` (dates × tickers)
    exposes the active stop level per held name after ``apply`` — plot it to *see* where
    the exit should land.
    """

    name = "stop_loss"
    requires = ("high", "low")

    def __init__(self, pct: float = 0.05, trailing: bool = True,
                 reentry_days: int | None = None):
        if not 0 < pct < 1:
            raise ValueError("pct must be in (0, 1), e.g. 0.05 for a 5% stop")
        if reentry_days is not None and reentry_days < 1:
            raise ValueError("reentry_days must be >= 1 (or None to wait for the signal)")
        self.pct = pct
        self.trailing = trailing
        self.reentry_days = reentry_days
        self.levels_: pd.DataFrame | None = None

    def apply(self, prices: pd.DataFrame, weights: pd.DataFrame,
              high: pd.DataFrame | None = None, low: pd.DataFrame | None = None,
              **panels) -> pd.DataFrame:
        # Run on the full daily price history (never reindexed to weight dates) so crashes
        # between rebalance dates are seen the day they happen.
        if high is None or low is None:
            log.info("stop_loss: no high/low panels — trailing and detection use closes only")
            high, low = prices, prices

        want = weights.reindex(prices.index).fillna(0.0) > 0
        keep = pd.DataFrame(1.0, index=prices.index, columns=weights.columns)
        levels = pd.DataFrame(np.nan, index=prices.index, columns=weights.columns)
        for ticker in weights.columns:
            keep[ticker], levels[ticker] = self._keep(
                prices[ticker].to_numpy(),
                high.reindex(prices.index)[ticker].to_numpy() if ticker in high else prices[ticker].to_numpy(),
                low.reindex(prices.index)[ticker].to_numpy() if ticker in low else prices[ticker].to_numpy(),
                want[ticker].to_numpy(),
            )
        self.levels_ = levels
        return (weights.reindex(prices.index).fillna(0.0) * keep).reindex(weights.index)

    def _keep(self, close: np.ndarray, high: np.ndarray, low: np.ndarray,
              want: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per-ticker ('allowed to hold', 'active stop level') series.

        Entry happens at day ``t``'s close, so the reference starts there and breach checks
        begin the next day. Each day the low is tested against the level carried in from
        yesterday, *then* the trail updates with the day's high.
        """
        keep = np.ones(len(close))
        level = np.full(len(close), np.nan)
        holding = False
        latched = False
        exit_t = -1
        ref = np.nan
        for t in range(len(close)):
            if latched:
                if not want[t]:
                    latched = False  # strategy exited on its own → release the latch
                elif self.reentry_days is not None and t - exit_t >= self.reentry_days:
                    latched = False  # cooldown served → back in at this close, stop re-armed
                    holding = True
                    ref = close[t]
                    continue
                else:
                    keep[t] = 0.0
                    continue
            if holding:
                stop_at = ref * (1 - self.pct)
                level[t] = stop_at
                if not np.isnan(low[t]) and low[t] <= stop_at:
                    keep[t] = 0.0  # touched intraday → out at this day's close
                    holding = False
                    latched = True
                    exit_t = t
                    continue
                if self.trailing and not np.isnan(high[t]) and high[t] > ref:
                    ref = high[t]
            elif want[t]:
                holding = True
                ref = close[t]  # entry fill; the day's earlier high predates the position
        return keep, level
