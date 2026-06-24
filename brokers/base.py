from abc import ABC, abstractmethod


class Broker(ABC):
    """Thin, swappable brokerage interface.

    Only what rebalancing needs: read account equity and current holdings, and place a
    whole-share market order. Keeping this minimal lets the broker (Alpaca paper now, IBKR
    later) sit behind one seam.
    """

    @abstractmethod
    def equity(self) -> float:
        """Total account value (cash + positions)."""
        ...

    @abstractmethod
    def positions(self) -> dict[str, float]:
        """Current holdings as ``{ticker: shares}``."""
        ...

    @abstractmethod
    def submit(self, ticker: str, qty: int, side: str) -> None:
        """Submit a market order. ``side`` is ``"buy"`` or ``"sell"``."""
        ...
