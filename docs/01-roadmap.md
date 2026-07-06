# Roadmap — from bare bones to a complete research platform

The detailed, step-by-step execution plan. `00-direction.md` says *why* and holds the coarse phases;
`03-research-platform.md` holds the platform design; this doc says **what to build, in what order, and what
"done" means for each step**. When this doc and the backlog disagree, this doc wins for sequencing.

## North star (restated, one paragraph)

A **trustworthy personal research backtester, evolving into automated paper trading** — *"a tool that doesn't
lie to me."* Daily bars, holds of ~1 day–6 months, rebalancing/reconstitution style. One authoring seam:
`strategy.weights(ctx)` over a point-in-time `DataContext`. Backtest = run it over history; screen = read its
last row; paper-trade = send that row to the broker — the same function on the same data, so research and live
can never drift. Every result is either bias-free or **labeled** with the biases it still carries. The end
state is a small set of honest strategies running unattended against a paper account, with reconciliation
proving the backtest and the account agree.

## Where we are (audited 2026-07)

The pipeline runs end-to-end and the test suite (48 tests, network-free) is green. Maturity by layer:

| Layer | State | What's actually proven |
| --- | --- | --- |
| Data: prices (yahoo/polygon/alpaca + parquet cache) | ✅ solid | Cached, deterministic re-runs. Per-ticker fetch; no data-quality checks; adjustment semantics not pinned. |
| Data: EDGAR fundamentals | ✅ v1 | Annual diluted EPS, as-first-filed, filed-date keyed, PIT-tested. No TTM / market-cap / SIC; concept handling is single-tag. |
| `DataContext` / universe / membership seam | ✅ solid | Outer-join + PIT ffill tested; `members = membership & price.notna()`. Mask is all-`True` (labeled biased). |
| Strategies (5) + registry | ✅ solid | Each ships a no-look-ahead test. |
| Engine (`bt`) + frequencies + stop-loss | ✅ solid | Frequencies and guardrail tested. **Frictionless** — no commissions/slippage/borrow. |
| Sweep + distribution report | ✅ solid | Selection-bias antidote works; chart carries the bias stamp. |
| Reporting (`run.py` path) | ◑ | Artifacts complete, but the bias stamp is only **logged** — the artifact files themselves are unstamped. |
| Multi-strategy compare | ✗ | Planned (Phase B remainder). |
| Survivorship-free universe | ✗ | The single biggest honesty gap — and it hides a data dependency (see M4). |
| Reproducibility enforcement | ✗ | Non-negotiable #4 has no mechanism: no golden files, no run manifest, no CI. |
| Paper trading | ◑ | Plan/preview/execute works against Alpaca paper. **Nothing is recorded** — no journal, no fill reconciliation, no scheduling. |
| Live paper / monitoring | ✗ | Future phase. |

## Gaps between the vision and today

**Trust gaps** — things that let a result lie, or make it unverifiable. These outrank features:

1. **Survivorship** (labeled, unfixed) — and the label understates the work: fixing `members` is useless
   without **prices for delisted names**, which yahoo does not serve. Names absent from the price panel are
   dropped at the data layer, so survivorship would persist even with a perfect historical mask.
2. **Costs and frictions** — `bt` runs frictionless. For monthly/quarterly turnover and the dollar-neutral
   short book, this flatters every headline number. Cheapest remaining honesty win (`bt` supports a
   commissions function natively).
3. **Incomplete bias stamping** — `run.py` logs the caveat but writes unstamped artifacts. An artifact
   separated from its log is an unlabeled backtest — the cardinal sin, on the main code path.
4. **No reproducibility enforcement** — nothing pins a result to its inputs (no manifest of args + data +
   git SHA), nothing catches a refactor that silently changes results (no golden file), no CI.
5. **Unpinned price semantics** — `yf.download` leaves `auto_adjust` to its default (the pending
   `FutureWarning`). Whether panels are total-return or price-return is currently an accident, and it must
   match the benchmark's treatment for alpha to mean anything.
6. **Paper execution drift is unmeasured** — market orders fill at whatever the market gives; the backtest
   assumes closes. Until fills are reconciled, the paper account can diverge from the research silently.

**Capability gaps** — promised by the design docs, not yet built: multi-strategy `compare`, TTM EPS,
market-cap + SIC panels, derived-features layer (rolling beta first), vol-targeting / position-cap /
max-drawdown guardrails, screener CLI, paper scheduling + reconciliation.

**Scaling gap** — the parquet cache is a *request* cache, not a data store. Its MD5 key is per
`(ticker, start, end, interval, source)`, so every new date window refetches from the network and stores an
overlapping copy; there is no coverage manifest ("what do I have for AAPL?"), no incremental top-up, no bulk
import path, and no policy for adjusted prices being retroactively restated by dividends/splits. The bytes are
a non-issue — full-history daily bars for *every* US equity including delisted fit in ~2–3 GB of parquet
(S&P 500 point-in-time is ~300 MB; a full-market close panel is ~0.4 GB of RAM) — the costs that explode with
more strategies and windows are **fetch time, API rate limits, and duplicate copies**, not disk.

**Hygiene gaps** — small, but each one is drift: `gtm.md` describes the *deleted* pre-redesign architecture
and a SaaS ambition that is not the north star (delete it; git is the history); `docs/08` retains stale
sections (a `--refresh` flag `run.py` doesn't have, "register in DataLoader" as the extension path);
`clean_ticker` makes a network call per benchmark; `polygon_fetcher` uses `print()`;
`data_ingestion/test_alpaca_fetch.py` is a scratch script in the package; `data/sp50.csv` (with its useful
CIK column) is unwired.

## Ordering principles

1. **Bare bones before features.** A feature on an untrusted base multiplies the lie. Trust rails (M0) come
   before anything new.
2. **Cheap honesty before expensive honesty.** Cost modeling is days (M1); survivorship is a data-procurement
   project (M4). Do the cheap one first, but start the M4 *decision spike* immediately — it gates the most
   valuable milestone and costs nothing to decide early.
3. **Every milestone ships whole.** "Fully fleshed out" is a contract: code + tests (no-look-ahead where the
   change touches signals/time/data) + docs updated + stamps/manifest extended + the backlog pruned. A
   milestone that skips one of these isn't done.
4. **Never remove a label without removing the bias.** Stamps only change when the underlying fix lands and is
   tested.

Dependency shape: **M0 → M0.5 → {M1, M2, M3 in any order} → M4 → M5 → M6 → M7**, with the M4.0 decision spike
run early in parallel. M0.5 (the canonical store) gates M4's bulk import. M6 (paper hardening) only depends on
M1 and can be pulled earlier if live learning matters more than universe honesty — but its reconciliation loop
is most valuable once costs (M1) exist to calibrate.

---

## M0 — Trust rails: make the bare bones provable

**Status: ✅ shipped 2026-07-03.** Manifest + stamped artifacts (`reporting/manifest.py`), golden-file test
(`tests/test_golden.py`), CI (`.github/workflows/ci.yml`), pinned `auto_adjust`, panel data-quality gate,
hygiene sweep (`gtm.md` deleted, `clean_ticker` network-free, polygon logger, scratch script removed).

**Why first:** correctness is the product, and today three non-negotiables (labeled biases, reproducibility,
no silent drift) have no enforcement mechanism on the main path.

- [ ] **Run manifest.** Every output dir gets `manifest.json`: git SHA, full CLI args, strategy + params,
      guardrails, universe name + a hash of its CSV, date range, data source/interval, cost assumptions (none
      yet — say so), and **every bias stamp in force**. A result folder becomes self-describing evidence.
- [ ] **Stamp the artifacts, not the log.** The caveat goes into the tearsheet title, the explorer title
      (as `research/report.py` already does for sweeps), and a header row in `stats.csv`/`metrics.csv`.
- [ ] **Golden-file reproducibility test.** A small pinned backtest on committed fixture data whose equity
      curve is asserted to high precision. Any refactor that changes results now fails loudly.
- [ ] **CI.** GitHub Actions running `pytest -q` (the suite is already network-free) on push/PR.
- [ ] **Pin price semantics.** Set `auto_adjust` explicitly in `yahoo_fetcher`, document that panels are
      adjusted (total-return) closes, and assert the benchmark gets the same treatment.
- [ ] **Panel sanity checks.** At `build_context`: raise on non-positive prices and duplicated dates; log
      named warnings for extreme one-day moves (data errors masquerade as alpha).
- [ ] **Hygiene sweep.** Delete `gtm.md`; fix the stale `docs/08` sections; drop `clean_ticker`'s network
      validation; `polygon_fetcher` prints → logger; move `test_alpaca_fetch.py` out of the package or delete.

**Done means:** a fresh clone + pinned env reproduces the golden file bit-for-bit; CI is green; every artifact
directory carries its manifest and stamps. **Still carried (stamped):** survivorship, frictionless costs.

## M0.5 — Canonical price store: fix the cache before it grows

**Status: ✅ shipped 2026-07-03** as `core/store.py` (per-ticker additive parquet + `coverage.json`, gap-only
fetching, one-vendor-per-ticker guard, `forget()` for adjusted-price refresh; daily prices routed through it,
intraday stays on the legacy cache). Design deviation from the sketch below: per-ticker files instead of
year-partitioned hive layout — simpler incremental appends, same DuckDB-scannable dataset.

**Why now:** the MD5 cache is keyed per `(ticker, start, end, interval, source)`, so every new date window
refetches from the network and stores an overlapping copy — the cost of growth is fetch time and rate limits,
not bytes. And M4's delisted-inclusive data arrives as a bulk file that today has nowhere to land. The volumes
stay trivial (full-market daily history 2000→now ≈ 2–3 GB parquet; point-in-time S&P 500 ≈ 300 MB; a
full-market close panel ≈ 0.4 GB RAM), so **no server database** — at this scale a parquet dataset, optionally
queried through DuckDB, beats Postgres/Timescale on every axis that matters here.

- [ ] Long-format parquet dataset — `date, ticker, open, high, low, close, adj_close, volume, source` —
      hive-partitioned by year under `data_store/`.
- [ ] Per-ticker coverage manifest (first/last stored date, source, last-refreshed) enabling **incremental
      ingest**: fetch only the gap since the last stored bar, never a full-range re-download.
- [ ] Adjusted-price refresh policy. Adjusted series are retroactively restated by every split/dividend, so a
      cached copy silently diverges from a fresh fetch. v1: record the fetch date, full-refresh a ticker on a
      detected corporate action (or periodically), and state the policy in the run manifest. When M4's vendor
      data lands with raw + adjusted columns, adopt theirs.
- [ ] `PriceSource` reads from the store through the existing seam — `build_context` and every strategy
      unchanged. Optionally register a DuckDB view over the dataset for ad-hoc SQL.
- [ ] Bulk-import path: ingest a vendor file (the M4 landing zone) into the same schema in one call.
- [ ] Retire the MD5 request cache after migration; keep EDGAR facts on the same long-format convention.
- [ ] Tests: ingest idempotency (re-ingest = no-op), gap-fill correctness, and store→panel equivalence against
      the current loader on a committed fixture — the M0 golden file must still match.

**Done means:** any backtest window is served from one canonical store with at most a gap-fetch; re-running a
sweep downloads nothing; results are unchanged (golden file green).

## M1 — Cost realism: stop flattering returns

**Status: ✅ machinery shipped 2026-07-03; frictionless default kept by decision.** `--cost-bps` wires
commission+slippage through `bt`'s commissions hook; turnover is reported; tests pin that costs bite. The
owner's call: at a sub-$1M book in liquid large/mid caps, slippage is immaterial — so the default stays `0`,
and every frictionless run is **stamped** "frictionless … returns are optimistic" in the manifest and on the
artifacts. The paper-trading reconciliation loop (M6) measures real slippage to revisit this with data.

- [ ] Commission + slippage as bps-of-notional via `bt`'s commissions hook; `--cost-bps` on `run.py`/`sweep.py`
      with a **nonzero default** (opting *into* frictionless should be the explicit act).
- [ ] Report turnover (from `bt`) so the cost sensitivity of a strategy is visible.
- [ ] Short borrow: v1 is a stamp, not a model — add "short borrow unmodeled" to the manifest for any
      strategy with negative weights. (A crude annual-bps borrow charge is a later refinement.)
- [ ] Tests: nonzero costs strictly reduce net returns for any strategy with turnover; zero-cost path still
      matches the M0 golden file.

**Done means:** every report is net-of-costs by default, with assumptions in the manifest.
**Still carried:** survivorship, borrow.

## M2 — Research bed completion (Phase B remainder)

**Status: held by decision (2026-07).** Build when multi-strategy comparison is actually needed; the shape is
agreed (one `bt.run(*tests)`, combined metrics table, overlaid explorer — same stamps and manifest as `run.py`).

- [ ] `research/compare.py`: `compare(specs, ctx, benchmark)` → one `bt.run(*tests)`, a combined
      alpha/beta/Sharpe/drawdown table, and an overlaid equity explorer. CLI entry point. This closes the old
      "portfolio comparison view."
- [ ] Small parameter-grid support on one strategy through the same path (the `vectorbt` trigger stays
      defined: revisit only when grids of hundreds of configs actually bottleneck).
- [ ] First derived feature: `features/beta.py` — rolling CAPM beta from trailing windows only, exposed as a
      context panel. Starts the `features/` layer with the simplest price-only case.
- [ ] Tests: compare determinism + smoke; rolling-beta no-look-ahead (truncation test on the feature panel).

**Done means:** the five built-ins compared over `sp500` with one command, stamped and manifested.

## M3 — EDGAR expansion (Phase C remainder)

**Status: ◑ mostly shipped 2026-07-03.** CIK overlay from committed CSVs, basic-EPS fallback, `eps_ttm`
(Q4 = FY − ΣQ1..3, PIT-tested), `shares` panel (market cap = `price × shares`), SIC via `fetch_submissions` /
`sic_meta`, and **`fetch_company_facts`** — the full 10-K/10-Q line-item history per company, every fact keyed
to its `filed` date, cached to `data_store/edgar/`: the structured ingest new fundamental panels build on.
Open: a proving strategy on the new panels, and the `frames` API if per-CIK fetching gets slow.

- [ ] **CIK from the universe file.** Use the `CIK` column already in `data/sp500.csv`/`sp50.csv` when
      present — kills ticker-mismatch and a network call. Wire `sp50` (or a generic `--universe-file`) while
      touching this.
- [ ] **Concept normalization.** `EarningsPerShareDiluted` with an explicit, logged fallback to `…Basic`.
- [ ] **TTM EPS** as an `eps_ttm` panel: Q4 = FY − Σ(Q1..Q3), as-first-filed, filed-date keyed, with its own
      PIT test. The annual panel stays (it's unambiguous; TTM is responsive — strategies choose).
- [ ] **Market cap**: `dei:EntityCommonStockSharesOutstanding` (PIT-ffilled) × price → `market_cap` panel + test.
- [ ] **SIC** from the `submissions` endpoint → `ctx.meta`, enabling sector-neutral books and comparables.
- [ ] A proving strategy for the new panels (e.g. sector-neutral `ls_pe`, or "most volatile of the top-N by
      market cap") — with its no-look-ahead test, per the credibility gate.
- [ ] Optional perf: the `frames` API for universe-scale concept fetches if per-CIK calls get slow.

**Done means:** `ls_pe` can run on TTM P/E; a size/sector screen exists; every new panel is PIT-tested.

## M4 — Survivorship (Phase D): the honesty milestone

**Status: pending — the data-source decision (M4.0) is the open gate.**

**The stakes:** this is the label every report carries and the one the whole design promises to remove. Expect
results to get *worse* when it lands — that is the point. Membership must be true point-in-time at
reconstitution granularity: a name selected one quarter and filtered out at the next reconstitution date
enters and leaves `ctx.members` on exactly those dates — holding it in between is history, holding it after is
a lie.

**Scope note (2026-07): the universe is not only equities.** Exchange-traded exposure to other asset classes —
oil, gold, broad commodities, rates — belongs in the tradable set too. Mechanically the seam already allows it
(they're tickers with daily bars behind the same `members` mask), but honesty differs by wrapper: ETPs like
GLD/USO carry roll yield, expense ratios, and contango drag that a price backtest silently includes (fine —
it's the tradable's real return) — the *survivorship* question is milder (few delistings) while the
*fundamentals* panels simply don't apply. Model: a composite universe (equities + a curated ETP list), each
component labeled with its own caveats.

**The hidden dependencies, named loudly:**

- Historical membership alone is **not enough** — delisted names need *price data*, and yahoo doesn't have it.
  Without a delisted-inclusive price source, a perfect mask changes nothing.
- Tickers drift (FB→META, share-class changes); the EDGAR CIK join and the price join both need a mapping
  that's correct *at each point in time*.

- [ ] **M4.0 Decision spike (start now, in parallel with M1–M3).** Evaluate: Wikipedia S&P change-log
      (free membership history, **no** delisted prices) vs Sharadar (cheap, delisted-inclusive prices +
      tickers-over-time) vs Norgate (built for exactly this). Write the decision + cost into
      `04-backlog.md` §3. This gates everything below; deciding costs nothing and unblocks budgeting.
- [ ] **M4.1 Membership history** into the `SP500` universe: a committed, deterministic membership file
      filling the real point-in-time mask through the existing seam (zero strategy changes — that was the
      whole bet).
- [ ] **M4.2 Delisted-inclusive prices** as a price `PanelSource` implementation (new source name, bulk-imported
      into the M0.5 store).
- [ ] **M4.3 Delisting semantics** in the engine: position exits at the last traded price to cash. Verify
      `bt`'s behavior on a truncated series and pin it with an explicit delisting-scenario test.
- [ ] **M4.4 Time-aware ticker↔CIK mapping** so EDGAR panels join correctly on the historical universe.
- [ ] **M4.5 Flip the stamp** — only now: "point-in-time membership (source X, snapshot date Y)"; anything
      residual (e.g. pre-source-coverage windows) stays labeled.
- [ ] Tests: a known index deletion enters/exits the mask on the right dates; the backtest holds it only while
      it was a member; truncation no-look-ahead on the mask itself; before/after comparison archived (the
      honest record of how much the bias flattered results).

**Done means:** momentum sweep, `xs_momentum`, and `ls_pe` run on the true point-in-time universe including
delisted names, and the survivorship stamp is gone from those runs.

## M5 — Risk & volatility layer (Phase E)

**Status: authoring seam shipped 2026-07-03** — a strategy now carries its own overlays via the `guardrails`
attribute (a tuple of `Guardrail` instances, applied before any CLI ones), so new guardrails are pure
`Guardrail.apply` implementations with no CLI plumbing. The guardrails themselves (below) remain.

**Why after M4:** vol-targeting a survivorship-flattered, cost-free equity curve tunes knobs against a lie.
This was always the stated end-state ordering: cancel the biases, *then* focus on volatility.

- [ ] Guardrails through the existing registry: **position cap**, **max-drawdown kill-switch**,
      **volatility targeting** (portfolio-level scalar on trailing realized vol), **sector-exposure cap**
      (uses M3's SIC). Each with a no-look-ahead test (trailing data only).
- [ ] Portfolio risk report: rolling vol/beta, gross/net exposure, sector exposure — the "watch overall
      portfolio risk" view from the north star, as reporting only (never a second ledger).

**Done means:** `--vol-target`, `--max-dd`, `--position-cap` compose on any strategy, tested.

## M6 — Paper trading hardening (complete direction-roadmap step 4)

**Status: ◑ core shipped 2026-07-03.** Order journal (`engine/journal.py`, append-only JSONL of every
plan/execution), fill reconciliation (`paper_trade.py --reconcile` — slippage in bps, missing/unplanned
flagged), and the ops guide incl. launchd scheduling and the no-server decision (`docs/05-paper-trading.md`).
Open: the drift monitor and alerting.

**Why:** the paper account is the platform's first contact with reality; today that contact leaves no record.

- [ ] **Order journal.** Append-only record (JSONL or SQLite) of every plan, submission, and fill — before
      any scheduling exists. An unrecorded trade is a silent failure.
- [ ] **Fill reconciliation.** After each run: fetch fills, diff vs the plan and vs the backtest-assumed
      close → a slippage report. Feed measured slippage back into M1's cost parameters — this closes the
      research↔live loop and is the payoff of the whole design.
- [ ] **Scheduling + idempotency.** Cron/launchd recipe; an `--as-of` guard so a same-day re-run is a no-op;
      explicit handling for market-closed, rejected orders, partial fills (raise or log narrowly — never
      swallow).
- [ ] **Drift monitor.** Paper equity vs the backtest's expectation over the same window; alert past a
      threshold.

**Done means:** one month of scheduled paper runs, each leaving journal + reconciliation artifacts, and a
measured slippage number plugged into the cost model.

## M7 — Live paper & ops hardening (direction-roadmap step 5)

Only after M6 has produced a month of evidence.

- [ ] Alerting (failure, drift breach), restart-safe state (broker positions + journal are the only state),
      documented recovery runbook, key handling review.

---

## Parking lot (deliberately not now)

**The document/alt-data lake** (raw 10-K/10-Q filings as text, earnings-call transcripts, news, LLM
evaluations, sentiment scores): explicitly deferred by decision (2026-07). When it comes, the shape is already
settled — *derived, point-in-time panels* enter through the same `PanelSource` seam (`requires=("sentiment",)`),
each value keyed to its publication timestamp (the `filed`-date analog), with raw documents stored beside the
store under `data_store/` and processed offline while the screener path reads only the derived panels. The
structured-fundamentals half of this already exists (`fetch_company_facts`).

Also parked: `vectorbt` (trigger: parameter grids actually bottleneck); server/columnar databases (Postgres,
Timescale, ClickHouse — unjustified at daily-bar scale, revisit only if intraday ever enters scope, which it
shouldn't); DSL/YAML strategy authoring; any GUI/dashboard; anything monetization-shaped — **decided 2026-07:
this is a personal instrument, not a product** (`gtm.md` deleted; the one lesson worth keeping — "tests are
the credibility gate" — is already `AGENT.md` law).

## Decisions this roadmap forces (and when)

| Decision | Needed by | Notes (`04-backlog.md` §3 tracks these) |
| --- | --- | --- |
| Survivorship data source (free reconstruction vs Sharadar vs Norgate) | **now** (M4.0 spike) | Gates M4; delisted *prices*, not just membership, decide it. |
| Adjusted-price refresh policy (as-fetched + refresh vs raw + factors) | ✅ decided 2026-07 | As-fetched + `PriceStore.forget()` for refresh; new data wins on overlap; M4 vendor data supersedes. |
| Multi-asset (ETP) universe composition | with M4 | Which oil/gold/commodity wrappers enter the tradable set, and their caveat labels. |
| Default cost level (`--cost-bps`) | ✅ decided 2026-07 | Frictionless (0) accepted for a <$1M book in liquid large/mid caps — stamped on every artifact; revisit with M6's measured slippage. |
| Annual vs TTM EPS as `ls_pe` default | M3 | Keep both panels; strategy chooses explicitly. |
| `sp50` universe wiring (named vs `--universe-file`) | M3 | Its CIK column is wanted either way. |
| Borrow-cost modeling beyond a stamp | after M6 | Revisit once real short fills exist. |
