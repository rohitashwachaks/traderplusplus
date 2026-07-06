from abc import ABC, abstractmethod

import pandas as pd

_REGISTRY: dict[str, type["Guardrail"]] = {}


def register(name: str):
    """Register a guardrail class under ``name`` for lookup via :func:`create`."""
    def decorator(cls: type["Guardrail"]) -> type["Guardrail"]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def create(name: str, **kwargs) -> "Guardrail":
    if name not in _REGISTRY:
        raise ValueError(f"Unknown guardrail '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)


def available() -> list[str]:
    return sorted(_REGISTRY)


class Guardrail(ABC):
    """A risk overlay on a strategy's target weights.

    A guardrail rewrites the weights a strategy proposes — it may only *reduce* exposure
    (push a weight toward 0), never increase it. Guardrails compose: the engine applies a
    list of them in order, **after** reconstitution sampling, and any change a guardrail
    makes trades immediately — a risk exit never waits for the next scheduled rebalance.

    Like strategies, a guardrail must be **no look-ahead**: the adjusted weight on day
    ``t`` may use information only through day ``t`` (intraday high/low of ``t`` included —
    they precede or coincide with ``t``'s close, where the exit fills).
    """

    name: str
    requires: tuple[str, ...] = ()  # extra panels beyond close, e.g. ("high", "low")

    @abstractmethod
    def apply(self, prices: pd.DataFrame, weights: pd.DataFrame, **panels) -> pd.DataFrame:
        """Return adjusted target weights, same shape/index as ``weights``.

        ``panels`` carries the guardrail's ``requires`` panels when the context has them
        (e.g. ``high=`` / ``low=``); a guardrail must degrade loudly-but-gracefully when
        they are absent (sweeps and tests run on close-only data).
        """
        ...
