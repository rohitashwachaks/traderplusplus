from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict


class StrategyBase(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """
        Unique strategy name for identification.
        """
        pass

    @abstractmethod
    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        For each asset (symbol), return a DataFrame of signals.
        Output: { 'AAPL': DataFrame, 'MSFT': DataFrame, ... }
        Each DataFrame must include 'signal' and 'position' columns.
        """
        pass

    @abstractmethod
    def generate_allocations(
            self,
            signals: Dict[str, pd.DataFrame],
            portfolio_cash: float,
            market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, int]:
        """
        Returns how many **shares** to buy per asset symbol.
        Output: { 'AAPL': 4, 'MSFT': 3 }
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
