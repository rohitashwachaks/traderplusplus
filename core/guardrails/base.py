from abc import ABC, abstractmethod
from typing import Dict


class Guardrail(ABC):
    @abstractmethod
    def evaluate(self, positions: Dict[str, int], prices: Dict[str, float]) -> Dict[str, bool]:
        """
        Evaluate which positions should be exited.

        Returns:
            Dict of ticker → True if it should be force-sold
        """
        pass