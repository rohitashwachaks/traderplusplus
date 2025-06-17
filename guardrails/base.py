from abc import ABC, abstractmethod
from typing import Dict


class GuardrailBase(ABC):
    def __init__(self):
        # Name will be set by the factory decorator
        self.name = getattr(self, 'name', None)

    @abstractmethod
    def evaluate(self, positions: Dict[str, int], prices: Dict[str, float]) -> Dict[str, bool]:
        """
        Evaluate which positions should be exited.

        Returns:
            Dict of ticker → True if it should be force-sold
        """
        pass

    def register_entry(self, ticker, avg_fill_price):
        """
        Register a new position entry
        :param ticker:
        :param avg_fill_price:
        :return:
        """
        pass

    def unregister(self, ticker):
        """
        Unregister a position (called on full exit)
        :param ticker:
        :return:
        """
        pass


class GuardrailFactory:
    _registry = {}

    @classmethod
    def register(cls, name: str):
        def decorator(guardrail_cls):
            guardrail_cls.name = name  # Set the name attribute on the class
            cls._registry[name] = guardrail_cls
            return guardrail_cls
        return decorator

    @classmethod
    def create_guardrail(cls, name: str, **kwargs) -> GuardrailBase:
        if name not in cls._registry:
            raise ValueError(f"Guardrail '{name}' not registered.")
        return cls._registry[name](**kwargs)

    @classmethod
    def get_supported_guardrails(cls) -> set:
        """
        Return all registered strategy names
        :return:
        """
        return set(cls._registry.keys())
