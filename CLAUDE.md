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
  `docs/00-direction.md`; the universe-first / point-in-time research platform is in
  `docs/03-research-platform.md`.

## Think holistically; surface blindspots before building

Before implementing, interrogate the *framing*, not just the task — the most dangerous assumptions are the ones
baked into the request. (This section exists because line-level no-look-ahead rigor once masked deeper
selection / survivorship / point-in-time biases that went unchallenged for too long.)

- Ask *what question is this actually answering, and is the design valid?* — not only *is the code correct?*
  Component-level correctness can mask methodology-level emptiness.
- Enumerate the blindspots and bias classes (`AGENT.md` non-negotiable 6) and name your assumptions **out loud,
  before** writing code.
- Push back when an approach has a hole — even when the user asked for it directly. Faithfully following a
  flawed premise is not help.
- Optimise for the user's learning and growth, not their agreement. The user writes code too and wants depth of
  perspective and honest challenge — bring the outside view; don't pander or hide blindspots.
