# Trader++ Documentation

Trader++ is a personal research backtester built on [`bt`](https://pmorissette.github.io/bt/) (engine) with
`ffn` + `quantstats` (metrics). The goal is correctness — *"a tool that doesn't lie to me."*

## Contents

- **[Direction & Roadmap](./00-direction.md)** — what we're building, current state, and next steps. Start here.
- **[Getting Started](./02-getting-started.md)** — install, run a backtest, add a strategy, run tests.
- **[Data Ingestion & Sources](./08-data-ingestion.md)** — Yahoo / Polygon / Alpaca fetchers and the cache.

Coding rules for agents and contributors live in [`../AGENT.md`](../AGENT.md).

> The earlier per-module docs (executors, contracts, guardrails, analytics, the hand-rolled engine) were
> removed when that code was retired in favour of `bt`. They documented modules that no longer exist.

---

**Version**: 0.1.0
