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
    list of them in order. Like strategies, a guardrail must be **no look-ahead** — the
    adjusted weight on day ``t`` may depend only on prices through ``t-1``.
    """

    name: str

    @abstractmethod
    def apply(self, prices: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
        """Return adjusted target weights, same shape/index as ``weights``."""
        ...
