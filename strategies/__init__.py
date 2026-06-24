"""Importing this package registers all built-in strategies."""
from strategies import buy_n_hold, momentum  # noqa: F401  (import triggers registration)
from strategies.base import available, create
