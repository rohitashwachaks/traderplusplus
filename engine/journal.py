"""Append-only journal of paper-trading activity — an unrecorded trade is a silent failure.

Every plan, execution, and reconciliation appends one JSON line. Events are never mutated or
deleted; the journal plus the broker's own records are the complete audit trail, and the
input the reconciliation step diffs against.
"""
import json
import os

import pandas as pd


def record(path: str, kind: str, payload: dict) -> dict:
    """Append one event (timestamped, with ``kind``) and return it."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    event = {"ts": pd.Timestamp.now().isoformat(timespec="seconds"), "kind": kind, **payload}
    with open(path, "a") as fh:
        fh.write(json.dumps(event, default=str) + "\n")
    return event


def read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def last(path: str, kind: str) -> dict | None:
    """The most recent event of ``kind``, or ``None``."""
    events = [e for e in read(path) if e.get("kind") == kind]
    return events[-1] if events else None
