from abc import ABC, abstractmethod


class StrategyBase(ABC):
    """Abstract base class for all trading strategies."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_name(self) -> str:
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

