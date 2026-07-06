# Paper Trading — execution, audit trail, and operations

How the paper-trading loop actually tracks and executes orders, and how to run it unattended.
For flags and a quickstart see `docs/02-getting-started.md`.

## How an order happens

The whole loop is the research seam pointed at a broker — there is no second code path:

```text
weights(ctx) → last row = today's target book
            → diff vs live Alpaca paper positions (engine/paper.build_plan)
            → whole-share market orders, sells first
            → journal (always) → submit (only with --execute)
```

- `python paper_trade.py --strategy=... --tickers=...` **previews** the plan and journals it.
- `--execute` submits the orders to Alpaca **paper** (the broker seam asserts a paper host —
  it cannot hit a live account) and journals the executed plan.
- Every run appends to an **append-only journal** (`output/paper/journal.jsonl` by default):
  the target weights, the reference closes the plan was sized on, account equity, and each
  order. An unrecorded trade is a silent failure; the journal is the audit trail.

## Reconciliation — did reality match the plan?

```bash
python paper_trade.py --reconcile
```

Fetches the broker's order history since the last executed plan and diffs it: per order,
planned vs filled quantity, the reference close vs the actual average fill, and the signed
**slippage in bps** (positive = the fill cost money vs what the backtest assumed). Statuses:
`filled` / `partial` / `missing` (planned but never reached the broker) / `unplanned` (the
broker did something the journal doesn't know about — investigate, always). The report is
printed and journaled.

The slippage numbers are the empirical answer to "what should `--cost-bps` be?" — measured
from your own fills, not guessed.

## Timing — matching the backtest's execution lag

The backtest's contract is *decide on day t's close, fill at day t+1's close*. To reproduce
that live, run the rebalance **shortly before the close** (~15:45–15:50 ET): the last complete
daily bar is yesterday's (t), and a market order submitted then fills ≈ today's close (t+1) —
the same lag the backtest assumes. Running after hours instead queues market orders for the
next **open**, a systematically different price; the reconciliation report will show that
drift if you choose it. Reconcile the next morning, after fills settle.

## Do I need a server? No

Daily bars mean **one short run per trading day** — this is a scheduling problem, not a
hosting problem. In order of escalation:

| Option | When it's right |
|---|---|
| **launchd on the Mac** (now) | Runs at a calendar time; a job missed while asleep fires on wake. Zero new infrastructure, secrets stay in `.env`. Miss = the Mac was off all day — acceptable for paper. |
| GitHub Actions cron | Off-machine and free, but API keys move to repo secrets and you debug in CI. Only worth it if the Mac is often off at 15:45 ET. |
| $5 VPS / Raspberry Pi | The live-paper phase (M7) — when a missed run costs money and you want monitoring/alerting on a box that is always up. Not before. |

launchd recipe (`~/Library/LaunchAgents/com.traderpp.rebalance.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.traderpp.rebalance</string>
  <key>ProgramArguments</key><array>
    <string>/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python</string>
    <string>paper_trade.py</string>
    <string>--strategy=xs_momentum</string>
    <string>--tickers=AAPL,MSFT,NVDA</string>
    <string>--execute</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/rchaks/Code/Trading/traderplusplus</string>
  <key>StartCalendarInterval</key><dict>
    <key>Weekday</key><integer>1</integer><!-- one block per weekday 1–5 -->
    <key>Hour</key><integer>12</integer><key>Minute</key><integer>45</integer><!-- 15:45 ET = 12:45 PT -->
  </dict>
  <key>StandardOutPath</key><string>output/paper/launchd.log</string>
  <key>StandardErrorPath</key><string>output/paper/launchd.err</string>
</dict></plist>
```

`launchctl load ~/Library/LaunchAgents/com.traderpp.rebalance.plist` to install; add a second
job for a morning `--reconcile`. Preview (no `--execute`) for a week before trusting it.

## Stops in live trading

The backtest's stop-loss approximates a resting stop order (trail on highs, trigger on the
low touching the level, fill at that day's close). Live, you can do strictly better: Alpaca
supports **native trailing-stop orders** (`type=trailing_stop`, `trail_percent`), which
trigger intraday at the broker with no monitoring loop on your side. Submitting one alongside
each entry is a natural M6/M7 upgrade — the backtest's close-fill approximation is the
*conservative* model of exactly that order (see `04-backlog.md`).

## What's still pending (roadmap M6/M7)

Drift monitoring (paper equity vs the backtest's expectation over the same window, with an
alert threshold) and alerting on failures. The journal already captures the inputs both need.
Broker-side trailing-stop orders (above) are the other candidate.
