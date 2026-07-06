# Trader++ Documentation

Trader++ is a personal research backtester built on [`bt`](https://pmorissette.github.io/bt/) (engine) with
`ffn` + `quantstats` (metrics). The goal is correctness — *"a tool that doesn't lie to me."*

## Contents

- **[Direction & Roadmap](./00-direction.md)** — what we're building, current state, and next steps. Start here.
- **[Roadmap](./01-roadmap.md)** — the detailed execution plan: gap analysis, milestones M0–M7 with exit
  criteria, and the decisions each one forces.
- **[Getting Started](./02-getting-started.md)** — install, run a backtest, sweep a universe, add a strategy, tests.
- **[Research Platform](./03-research-platform.md)** — universe-first, point-in-time design: `DataContext`,
  universe, EDGAR fundamentals, the bias reckoning, and the phased roadmap.
- **[Backlog & Open Decisions](./04-backlog.md)** — planned features, ideas to explore, decisions to revisit.
- **[Paper Trading](./05-paper-trading.md)** — how orders execute, the journal + fill reconciliation, and
  running unattended (launchd — no server needed).
- **[Data Ingestion & Sources](./08-data-ingestion.md)** — Yahoo / Polygon / Alpaca / EDGAR fetchers, the cache,
  and how raw data becomes a `DataContext`.

Coding rules for agents and contributors live in [`../AGENT.md`](../AGENT.md).

> The earlier per-module docs (executors, contracts, guardrails, analytics, the hand-rolled engine) were
> removed when that code was retired in favour of `bt`. They documented modules that no longer exist.

---

**Version**: 0.1.0
