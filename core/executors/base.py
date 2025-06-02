from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    @abstractmethod
    def submit_order(self, order):
        """Submit an order to the execution engine."""
        pass

    @abstractmethod
    def cancel_order(self, order_id):
        """Cancel an open order by ID."""
        pass

    @abstractmethod
    def get_portfolio(self):
        """Return the current portfolio state."""
        pass

    @abstractmethod
    def get_order_status(self, order_id):
        """Get the status of an order by ID."""
        pass

    @abstractmethod
    def sync_portfolio(self):
        """Sync portfolio state with broker or simulation."""
        pass

    @abstractmethod
    def step(self, current_time):
        """Advance simulation or poll live broker to next time step."""
        pass
