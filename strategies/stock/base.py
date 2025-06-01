from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict

from core.market_data import MarketData


class StrategyBase(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """
        Unique strategy name for identification.
        """
        pass

    @abstractmethod
    def generate_signals(
        self,
        market_data: MarketData,
        current_date: pd.Timestamp,
        lookback_window: int = 60
    ) -> Dict[str, int]:
        """
        For each asset (ticker), return the current trading signal.
        Output: { 'AAPL': 1, 'MSFT': -1, 'SPY': 0 }
        Each signal should be:
        - 1 for Buy
        - -1 for Sell
        - 0 for Hold
        Strategy must not look ahead beyond `current_date`.
        """
        pass


class StrategyFactory:
    _registry = {}

    @classmethod
    def register(cls, name):
        def decorator(strategy_cls):
            cls._registry[name] = strategy_cls
            return strategy_cls
        return decorator

    @classmethod
    def create_strategy(cls, name: str, **kwargs) -> StrategyBase:
        if name not in cls._registry:
            raise ValueError(f"Strategy '{name}' not registered.")
        return cls._registry[name](**kwargs)

    @classmethod
    def get_supported_strategies(cls) -> set:
        """
        Returns a list of all registered strategy names.
        """
        return set(cls._registry.keys())
