# CLAUDE.md

This project's guidance lives in a single source of truth to avoid drift. Read it:

@AGENT.md

## Claude Code specifics

- Treat the **Non-negotiables** and **Code hygiene** sections of `AGENT.md` as hard constraints, not
  suggestions. Correctness (no look-ahead bias, no silent failures, reconciled accounting) outranks speed.
- This is critical financial infrastructure. When a change touches signal generation, time iteration, or
  accounting, add or update a test in the same change — a no-look-ahead test where relevant.
- Prefer the smallest correct diff. Deleting dead code and collapsing duplication is welcome; speculative
  abstraction is not.
- Detailed rationale and the migration roadmap (custom engine → `bt`/`ffn`/`quantstats`) are in
  `docs/00-direction.md`.
