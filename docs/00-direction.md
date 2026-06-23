# Direction & Roadmap

Why this project is shaped the way it is, and where it's going. For day-to-day coding rules see `AGENT.md`.

## North star

A **trustworthy personal research backtester**, evolving toward automated paper trading. The product *is*
correctness — *"a tool that doesn't lie to me."* A fast, pretty, subtly-wrong backtest loses real money.

Constraints that drive every decision:

- **Horizon:** no intraday/HFT. Holds ~1 day to 6 months → **daily bars**.
- **Style:** rebalancing / reconstitution — *signal/score → target weights → rebalance*. Future signals may
  come from screeners and AI-agent / news sources, so strategies express **target weights**, not raw orders.
- **Portfolio = reporting / comparison view:** compare strategies' alpha/beta/Sharpe/drawdown/risk and track
  overall-portfolio risk. Not a second accounting system.
- **Trajectory:** research backtest → automated paper trading → live paper trading. Broker behind a thin,
  swappable interface (Alpaca paper first; IBKR a later swap).

## The pivot: adopt a proven engine

We are **retiring the hand-rolled backtest engine** and standing on proven libraries. Maintaining a bespoke
event loop is not where the value is, and a battle-tested engine retires our biggest trust risks for free.

Settled stack:

- **Engine:** [`bt`](https://pmorissette.github.io/bt/) — rebalancing-first, composable `Algo`s, multi-asset,
  free. A custom `Algo` turns any external score (screener / AI / news) into target weights.
- **Metrics:** `ffn` + `quantstats` — no hand-maintained Sharpe/alpha/beta/drawdown.
- `vectorbt` is held in reserve for heavy parameter-sweep research; event-driven engines (backtrader /
  nautilus) are deprioritized — they solve a latency problem we don't have.

### Keep / adapt / drop

- **Keep:** `data_ingestion/*` fetchers + `core/data_loader.py` parquet cache (library-agnostic, our most
  reusable asset); `strategies/base.py` as the authoring interface — reshaped around **target weights**.
- **Adapt:** `contracts/portfolio.py` → a reporting/comparison view over engine results.
- **Drop:** `core/backtester.py`, `core/market_data.py`, `executors/backtest.py` (engine replaces them);
  `analytics/*` + `utils/metrics.py` (use `ffn`/`quantstats`); `strategies/derivatives/*` (out of scope).

## Roadmap

0. **Lock the baseline.** Run the current engine end-to-end on one ticker, record final net worth + stats as
   the "before" reference any new engine must reproduce.
1. **Engine spike.** Stand up `bt` on one strategy fed by our data layer; reproduce the baseline curve.
2. **Strategy + portfolio layer.** Port working strategies to target weights; build the real multi-ticker
   rebalancing strategy (the current `capm_portfolio` is a stub); make Portfolio the comparison view.
3. **Trust & tests.** Golden-file tests, accounting-invariant tests, explicit no-look-ahead tests, CI.
4. **Automated paper trading.** On a schedule: recompute target weights → diff holdings → emit orders via a
   thin broker port (Alpaca paper first). Reconcile fills against backtest expectations.
5. **Live paper / hardening.** Promote to live paper; add monitoring, alerting, failure handling.

## Feasibility

High. ~2,500 LOC, cleanly layered; the hardest-to-get-right parts (data ingestion + caching) already work and
are library-agnostic. Adopting `bt` *reduces* surface area. The daily horizon makes paper trading simple —
"recompute weights on a schedule, diff holdings, send orders" — no live-parity engine required. Main one-time
cost: learning `bt` and re-expressing strategies as target weights.
