from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData


class StrategyBase(ABC):
    """
    Abstract base class for trading strategies.
    All strategies must implement get_name and generate_signals.
    """
    @abstractmethod
    def get_name(self) -> str:
        """
        Return unique strategy name for identification.
        """
        pass

    @abstractmethod
    def generate_signals(
        self,
        market_data: 'MarketData',
        current_date: pd.Timestamp,
        positions: Dict[str, Asset | CashAsset]
    ) -> Dict[str, int]:
        """
        For each asset (ticker), return the Number of shares to buy or sell.
        Output: { 'AAPL': 1, 'MSFT': -5, 'SPY': 0 }
        Each signal should be:
        - >0 : Long (number of shares to buy)
        - <0 : Short (number of shares to sell)
        - 0 : No action (hold)
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
        Return all registered strategy names
        :return:
        """
        return set(cls._registry.keys())