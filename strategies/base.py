from abc import ABC, abstractmethod

import pandas as pd

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
    """A strategy maps a price panel to target portfolio weights.

    This is the single authoring interface: a strategy is *signal -> target weights*,
    which covers rebalancing/reconstitution and (later) screener / AI / news signals.
    The engine rebalances the portfolio toward whatever weights are returned.

    Two frequencies tune *when* the engine acts (both default to daily = trade whenever the
    signal changes). A strategy can override them as class attributes, e.g. a quarterly
    rebalance with a yearly reconstitution sets ``rebalance_freq = "Q"`` and
    ``reconstitution_freq = "Y"``:

    - ``rebalance_freq`` — how often to trade back to the target weights (correct drift).
    - ``reconstitution_freq`` — how often to recompute the target (the selection + weights),
      held constant in between.
    """

    name: str
    rebalance_freq: str = "D"
    reconstitution_freq: str = "D"

    @abstractmethod
    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Return target weights aligned to ``prices`` (index = dates, columns = tickers).

        Each row holds the desired fraction of portfolio value per ticker; rows sum to at
        most 1 (the remainder stays in cash). **No look-ahead:** the weight on date ``t``
        may use price information only through ``t``. Strategies that act on a signal must
        apply their own one-bar lag here.
        """
        ...
