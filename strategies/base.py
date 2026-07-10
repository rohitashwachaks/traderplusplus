from abc import ABC, abstractmethod

import pandas as pd

from core.context import DataContext

_REGISTRY: dict[str, type["TargetWeightStrategy"]] = {}


def register(name: str):
    """Register a strategy class under ``name`` for lookup via :func:`create`."""
    def decorator(cls: type["TargetWeightStrategy"]) -> type["TargetWeightStrategy"]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def create(name: str, **kwargs) -> "TargetWeightStrategy":
    if name not in _REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)


def available() -> list[str]:
    return sorted(_REGISTRY)


class TargetWeightStrategy(ABC):
    """A strategy maps a :class:`~core.context.DataContext` to target portfolio weights.

    This is the single authoring interface: a strategy is *signal -> target weights*,
    which covers rebalancing/reconstitution and (later) screener / AI / news signals.
    The engine rebalances the portfolio toward whatever weights are returned. All data —
    price, membership, fundamentals — is read through the context, so a strategy never
    learns where a panel came from and new data sources don't change its code.

    Two frequencies tune *when* the engine acts (both default to daily = trade whenever the
    signal changes). A strategy can override them as class attributes, e.g. a quarterly
    rebalance with a yearly reconstitution sets ``rebalance_freq = "Q"`` and
    ``reconstitution_freq = "Y"``:

    - ``rebalance_freq`` — how often to trade back to the target weights (correct drift).
    - ``reconstitution_freq`` — how often to recompute the target (the selection + weights),
      held constant in between.

    ``single_asset`` marks a strategy whose rule is per-name and independent (e.g. an absolute
    trend filter): it is validated by *sweeping* it across a universe one name at a time and
    reading the distribution of outcomes, not by pooling names into one basket.
    """

    name: str
    rebalance_freq: str = "D"
    reconstitution_freq: str = "D"
    single_asset: bool = False
    requires: tuple[str, ...] = ()  # context panels beyond price/members, e.g. ("eps",)
    requires_meta: tuple[str, ...] = ()  # static classification columns, e.g. ("sector",)
    guardrails: tuple = ()  # risk overlays that ship *with* the strategy, applied before any CLI ones

    @abstractmethod
    def weights(self, ctx: DataContext) -> pd.DataFrame:
        """Return target weights aligned to ``ctx.price`` (index = dates, columns = tickers).

        Each row holds the desired fraction of portfolio value per ticker; rows sum to at
        most 1 (the remainder stays in cash; long/short books may sum to ~0). **No
        look-ahead:** the weight on date ``t`` may use information only through ``t``.
        Strategies that act on a signal must apply their own one-bar lag here. Only hold
        names that are in the universe on each date — mask by ``ctx.members``.
        """
        ...
