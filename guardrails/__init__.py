"""Importing this package registers all built-in guardrails."""
from guardrails import stop_loss  # noqa: F401  (import triggers registration)
from guardrails.base import available, create
