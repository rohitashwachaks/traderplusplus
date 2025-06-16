from abc import ABC, abstractmethod


class BaseExecutor(ABC):
    """
    Abstract base class for all execution engines (backtest, paper, live).
    Defines the required interface for submitting/cancelling orders and advancing simulation.
    """
    @abstractmethod
    def submit_order(self, order):
        """
        Submit an order to the execution engine.
        Args:
            order: Order object to submit.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id):
        """
        Cancel an open order by ID.
        Args:
            order_id: Unique order identifier.
        """
        pass

    @abstractmethod
    def get_portfolio(self):
        """
        Return the current portfolio state.
        Returns:
            Portfolio: The associated portfolio instance.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id):
        """
        Get the status of an order by ID.
        Args:
            order_id: Unique order identifier.
        Returns:
            OrderStatus: Status enum for the order.
        """
        pass

    @abstractmethod
    def sync_portfolio(self):
        """
        Sync portfolio state with broker or simulation.
        """
        pass

    @abstractmethod
    def step(self, current_time):
        """
        Advance simulation or poll live broker to next time step.
        Args:
            current_time: Current simulation or market time.
        """
        pass
