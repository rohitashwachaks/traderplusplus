"""Run manifest — every output directory carries the evidence of how it was produced.

Non-negotiable #4 (deterministic & reproducible) and #6 (label every bias) need a mechanism,
not a habit. ``manifest.json`` records the code version, the full configuration, the data
provenance, and **every bias stamp in force**, so a result folder found weeks later is
self-describing and re-derivable — or visibly not.
"""
import json
import logging
import os
import subprocess
from typing import Any

import pandas as pd

log = logging.getLogger("traderplusplus")


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def write_manifest(
    out_dir: str,
    *,
    command: str,
    args: dict[str, Any],
    strategy: Any,
    stamps: list[str],
    universe: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Write ``manifest.json`` into ``out_dir`` and return its path.

    Args:
        command: which entry point produced this (``run`` / ``sweep`` / ``paper``).
        args: the full parsed CLI arguments (``vars(args)``).
        strategy: the strategy instance; its name, frequencies and attached guardrails are
            recorded.
        stamps: every bias/assumption caveat in force — an empty list is itself a claim.
        universe: name / bias / file fingerprint of the universe, if any.
        extra: run-specific additions (e.g. turnover).
    """
    manifest = {
        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "command": command,
        "git_sha": git_sha(),
        "args": {k: v for k, v in sorted(args.items())},
        "strategy": {
            "name": strategy.name,
            "rebalance_freq": strategy.rebalance_freq,
            "reconstitution_freq": strategy.reconstitution_freq,
            "guardrails": [type(g).__name__ for g in strategy.guardrails],
        },
        "universe": universe,
        "bias_stamps": stamps,
    }
    if extra:
        manifest.update(extra)

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "manifest.json")
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    log.info("Manifest: %s", path)
    return path
