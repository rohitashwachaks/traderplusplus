"""Importing this package registers all built-in strategies."""
from strategies import buy_n_hold, cross_sectional_momentum, momentum  # noqa: F401  (registers)
from strategies.base import available, create
