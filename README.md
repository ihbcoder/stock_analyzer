# Stock Analyzer

Stock Analyzer is a research-only, rules-based momentum scanner for a user-defined stock watchlist. It downloads daily OHLCV data with `yfinance`, compares every stock with QQQ, stores each scan in SQLite, renders a static dashboard, and produces a daily status email plus a monthly action-oriented rebalance email.

It does **not** connect to a brokerage, place orders, guarantee returns, predict the future, or provide individualized investment advice. The output is a transparent research report that the account owner must review before making any trade.

## What the application is designed to answer

Given:

- a configured watchlist in `stocks.json` or `stocks_eod.json`; and
- the stocks actually held in the private `holdings.txt` file,

the application answers two different questions:

1. **Daily monitoring:** Which names in the watchlist currently have the strongest price momentum, and is the broad QQQ market regime healthy or weak?
2. **Monthly portfolio review:** For each current holding, should it be kept, sold for a stronger qualified stock, or sold with the released allocation directed to the QQQ/SPY fallback?

The default workflow is to scan daily after the close, collect history and monitor the report, then act only after reviewing the monthly action email on the first NYSE trading day of a new month after the close.

## Investment approach and theory

The model is a **cross-sectional momentum** system. It ranks the stocks in the configured watchlist by their past relative performance, rather than attempting to estimate intrinsic value or forecast earnings. The core idea is that stocks which have been stronger than their peers and the benchmark over intermediate horizons may continue to lead, while the portfolio should avoid repeatedly rotating over small score differences.

The design deliberately emphasizes intermediate-horizon relative strength (3, 6, and 12 months), gives the most recent month a smaller role as an acceleration signal, and uses longer moving averages and 52-week-high proximity as trend confirmation. This is directionally consistent with common academic momentum constructions, which often rank prior returns over an intermediate horizon and may exclude the most recent month. It is not a claim that the model will work in every period. Momentum strategies can experience substantial drawdowns and reversals.

Useful background:

- [Asness, Moskowitz, and Pedersen, *Value and Momentum Everywhere*](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf)
- [Jegadeesh and Titman, *Profitability of Momentum Strategies*](https://www.nber.org/papers/w7159)
- [Investor.gov: asset allocation and diversification](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)

QQQ and SPY are equity ETFs with substantial overlap. The QQQ/SPY fallback is intended to keep the portfolio invested when the model finds too few qualified individual-stock alternatives; it is **not** a cash substitute, a hedge, or a guarantee against losses.

## Quick start

Install the dependencies:

```powershell
cd C:\Users\k_buh\Code\stock_analyzer
py -m pip install -r requirements.txt
```

Run an after-close scan, save the result separately, and send the email report:

```powershell
py main.py scan .\stocks_eod.json --output .\results_eod.json --email-report
```

For an intraday/regular-hours scan:

```powershell
py main.py scan .\stocks.json --output .\results.json --email-report
```

Open the generated dashboard locally:

```powershell
py main.py serve --site-dir site --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000>.

Generate a text-only portfolio review at any time:

```powershell
py main.py rebalance --holdings-file holdings.txt
```

Do not use `results.json` or `results_eod.json` as the scan input. They are generated output files, not watchlists. Input validation rejects them.

## Configuration and private holdings

`stocks.json` and `stocks_eod.json` contain the public strategy/watchlist configuration. The relevant `agent` settings are:

| Setting | Default | Meaning |
|---|---:|---|
| `benchmark` | `QQQ` | Benchmark used for relative-return calculations and broad-market regime checks. |
| `minimum_score` | `70` | Minimum score for a new stock purchase. |
| `scoring_version` | `monthly_momentum_v2` | Identifies the scoring model so scores are compared only with compatible historical scans. |
| `minimum_average_dollar_volume` | `10000000` | Minimum 20-day average daily dollar volume required for a **new buy**. |
| `market_volatility_limit` | `0.30` | Maximum QQQ 20-day annualized volatility for new individual-stock purchases. |
| `market_hours_only` | `true` in `stocks.json`, `false` in `stocks_eod.json` | Whether to skip a scan when the NYSE is closed. |

`holdings.txt` is deliberately separate. It contains one ticker per line and represents the current portfolio. It is personal data: do not commit, publish, or replace it. The application never edits it. After reviewing and executing a desired rotation manually, update `holdings.txt` yourself so the next report reflects the actual portfolio.

## Data pipeline

For QQQ and every enabled ticker, the default `YFinanceProvider` requests approximately two years of daily OHLCV history. The scanner then calculates the indicators below and scores the latest available row. A missing ticker history becomes an `ERROR` row; a missing QQQ history causes the scan to fail because QQQ is required for relative-strength calculations.

Every result is written to:

- an output JSON file (`results.json` or the supplied `--output` path);
- SQLite (`data/stock_analyzer.db` by default); and
- static dashboard files in `site/`.

SQLite stores the scan timestamp, configuration source, score version, market status, benchmark/regime metrics, policy settings, ranked stocks, metrics, reasons, and risk flags. Database migrations preserve existing data. Older scans are labeled `legacy_v1`; score-change and rebalance comparisons use only `monthly_momentum_v2` runs.

## Indicators calculated for every stock

The program calculates the following daily indicators. Not every stored indicator is a score input; that distinction matters.

| Indicator | Calculation | Used for |
|---|---|---|
| 5d, 20d, 60d returns | Percentage change over 5, 20, and 60 trading days | Stored/displayed context. |
| 1m, 3m, 6m, 12m returns | Percentage change over 21, 63, 126, and 252 trading days | 1m/3m are buy gates; 3m/6m/12m drive relative-strength ranking. |
| 20-day EMA | Exponential moving average of close | Stored context. |
| 50-day SMA | Simple moving average of close | 10 score points if the close is above it. |
| 200-day SMA | Simple moving average of close | 10 score points if the close is above it; also used for QQQ market regime. |
| RSI-14 | Wilder-style 14-day RSI | Risk flag only when above 80; it does not add score. |
| Relative volume | Current volume divided by 20-day average volume | Stored context. |
| 52-week-high distance | Close divided by rolling 252-day high minus 1 | 15 score points if within 10% of the high; risk flag if more than 25% below it. |
| MACD, signal, histogram | 12/26 EMA MACD with 9-period signal | Stored context; not a current score input. |
| 20-day average dollar volume | Average of `close × volume` over 20 days | Liquidity filter for new buys. |
| 20-day annualized volatility | Standard deviation of daily returns over 20 days × `sqrt(252)` | QQQ market-regime filter. |

## Exact stock scoring model: `monthly_momentum_v2`

Each successfully calculated stock receives an integer score from 0 to 100. Missing data simply earns no points for that component.

| Component | Maximum points | Exact implementation |
|---|---:|---|
| Multi-horizon relative strength | 50 | For each ticker, calculate its excess return versus QQQ at 63, 126, and 252 trading days. Average the available excess returns. Rank that average across the successfully calculated watchlist using percentile rank. Award `round(50 × percentile)`. |
| One-month relative strength | 15 | Calculate 21-day stock return minus 21-day QQQ return. Rank it across the watchlist using percentile rank. Award `round(15 × percentile)`. |
| Above 50-day SMA | 10 | Award 10 when latest close is strictly above the 50-day simple moving average. |
| Above 200-day SMA | 10 | Award 10 when latest close is strictly above the 200-day simple moving average. |
| Near 52-week high | 15 | Award 15 when close is at least 90% of its rolling 252-day high (within 10% of the high). |
| **Total** | **100** | Sum of the components above. |

### What “relative” means

For a horizon `h`:

```text
stock relative return(h) = stock return(h) − QQQ return(h)
```

For example, if a stock rose 12% over 63 trading days and QQQ rose 5%, its 3-month relative return is +7 percentage points. The score then compares that result with the other configured stocks; a high percentile means the stock is a leader inside this particular watchlist.

This is not a universal market ranking. Changing the watchlist changes the percentile ranks and therefore can change scores.

### Signals

With the default `minimum_score` of 70, scores map to display signals as follows:

| Signal | Rule |
|---|---|
| `STRONG` | Score at least `max(minimum_score + 10, 80)`; default: 80–100. |
| `WATCH` | Score at least `minimum_score`; default: 70–79. |
| `NEUTRAL` | Score 55–69. |
| `WEAK` | Score below 55. |
| `ERROR` | Data retrieval or calculation failed for that ticker. |

### Reasons and risk flags

Each row contains machine-generated reasons for earned components, such as “Price is above the 200-day SMA,” and separate risk flags. Current risk flags are:

- `RSI is very extended` when RSI-14 is above 80; and
- `Far below the 52-week high` when the close is more than 25% below its 252-day high.

An RSI flag is not an automated sell instruction. Strong momentum can remain extended for long periods. The score and portfolio rules rely on the combination of relative strength, trend, rank, and persistence rather than a single RSI cutoff.

## Market regime and new-buy filters

The scanner separately classifies the QQQ regime as `HEALTHY` or `WEAK`.

The regime is `WEAK` when either condition is true:

1. QQQ latest close is at or below its 200-day SMA; or
2. QQQ 20-day annualized volatility is above `agent.market_volatility_limit` (30% by default).

In a weak regime, the application blocks **new individual-stock buys**. It does not automatically liquidate every current holding; holdings still follow the keep/sell rules below. If the portfolio has unused target weight, that weight goes to the 50/50 QQQ/SPY fallback.

A prospective new stock purchase must also satisfy all of these conditions:

1. It is not already in `holdings.txt`.
2. Its rank is inside the target stock-position count.
3. Its score is at least `buy_score` (70 by default).
4. Its raw 1-month (21-day) and 3-month (63-day) returns are both positive.
5. Its 1-month and 3-month returns relative to QQQ are both positive.
6. Its 20-day average dollar volume is at least the configured liquidity minimum.
7. The market regime is not weak.
8. If a compatible prior v2 scan exists, its score change is non-negative.

## How the monthly rebalance recommendation is formed

The recommendation is an allocation plan, not an order ticket. It uses the latest two complete `monthly_momentum_v2` runs and the tickers in `holdings.txt`.

### Target portfolio size and weighting

By default, the target number of individual stock positions equals the number of tickers currently in `holdings.txt`. This avoids an automatic reduction of a larger existing portfolio. Use `--top-n` only when you intentionally want a different number.

```powershell
py main.py rebalance --holdings-file holdings.txt --top-n 12
```

Each selected stock receives equal target weight of `100% ÷ target stock-position count`. If fewer selected stocks remain after the rules below, the unused weight is split equally between QQQ and SPY.

Example: a 12-stock target with 9 selected individual stocks assigns 8.33% to each selected stock, leaving 25%. The target then assigns 12.5% to QQQ and 12.5% to SPY.

### Keep and sell rules for current holdings

For each current holding:

| Result | Rule |
|---|---|
| `SELL` | The ticker is not ranked in the latest run. |
| `SELL` | Latest score is below `sell_score` (55 by default). |
| `KEEP` | Latest rank is inside the target position count. |
| `KEEP` | Latest rank is outside the target this run but was inside it in the prior compatible v2 run. This is the one-run grace period. |
| `SELL` | It has been outside the target group for two compatible runs. |
| `SELL` | It is a lower-scoring kept holding outside the final target portfolio size. |

### Rotation gap

To reduce churn, a holding that would be sold solely for being outside the top group remains a `KEEP` when no eligible new candidate has a score at least `rotation_score_gap` points higher. The default gap is 10 points.

This protection does **not** override a sell caused by a score below the sell threshold or a missing latest ranking.

### Buy, fallback, and destination logic

After retained holdings are counted, eligible new stocks fill the remaining target slots in rank order. If there are fewer eligible stocks than slots, the remaining allocation becomes:

```text
50% QQQ + 50% SPY
```

The report therefore distinguishes:

- `KEEP`: retain the current stock;
- `SELL` with destination `qualified stock replacements`: strong candidates filled the available stock slots; or
- `SELL` with destination `50% QQQ / 50% SPY`: no sufficient qualified individual-stock alternative exists for the unused allocation.

The target-allocation table is the authoritative summary of the intended post-review mix. It includes rows sourced from `KEEP`, `BUY`, and `FALLBACK`.

## Score change and interpretation

`Score Δ` is:

```text
latest v2 score − prior compatible v2 score
```

It is blank when no compatible prior v2 scan exists. Legacy scores are never used in this calculation because the previous model used a different formula. A positive change indicates that the stock has improved under this model; it does not by itself create a buy signal.

## Reports, dashboard, and email schedule

### Dashboard

Each successful scan regenerates:

- `site/index.html` — interactive dashboard;
- `site/results.html` — simplified static results page;
- `site/dashboard-data.json` — dashboard data; and
- `site/favicon.svg`.

The dashboard shows the latest rankings, metrics, risk flags, QQQ regime, current-holding actions, destinations, and target allocations. It uses `holdings.txt` when present; only when that file is absent does it fall back to `holdings_example.txt` and label it as example data.

### Email

The scheduled scan runs with `--email-report` and sends:

- **Daily successful-scan status email:** top rankings and the current rebalance snapshot for monitoring.
- **Monthly action email:** after close on the first NYSE trading day of a new month, the same day’s email subject becomes `MONTHLY REBALANCE ACTION REQUIRED`. Review the sell/buy/fallback plan before acting.
- **Failure email:** if the scan pipeline fails, the application attempts to email a `FAILED` report containing the error. The process still exits non-zero so Task Scheduler records the failure.

The schedule is based on the NYSE calendar, not merely the calendar month-end. The system does not automatically trade or modify `holdings.txt`.

## Commands

```powershell
# Scan using regular-hours policy (skips closed market)
py main.py scan stocks.json

# Scan after close; recommended for the daily end-of-day task
py main.py scan stocks_eod.json --output results_eod.json --email-report

# Show recent scan metadata and latest ranked names
py main.py report

# Filter latest report by signal
py main.py report --signal STRONG --top 10

# Build the current holdings review
py main.py rebalance --holdings-file holdings.txt

# Inspect saved scan prices/ranks for one ticker
py main.py prices NVDA

# Serve the static dashboard locally
py main.py serve --site-dir site --host 127.0.0.1 --port 8000

# Build a static deployment bundle
node build-site.mjs
```

`main.py` preserves backward compatibility with the older form `py main.py stocks.json ...` by treating the file name as the `scan` input.

## Automation

`scripts/run_scan.ps1` is the stable Task Scheduler entry point. The end-of-day configuration is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\k_buh\Code\stock_analyzer\scripts\run_scan.ps1" -InputFile "stocks_eod.json" -OutputFile "results_eod.json" -EmailReport
```

The recommended trigger is daily at 4:10 PM Eastern. `TASK_SCHEDULER.md` contains the complete Windows Task Scheduler setup and verification instructions.

`scripts/publish_site.ps1` runs a scan, stages generated public files, commits them, and pushes to `origin/main`. Do not run it unless publishing the generated dashboard is intended.

## Important limitations

- This is a long-only research tool. It does not short stocks, use options, use leverage, or connect to a broker.
- It does not include fundamentals, valuation, analyst estimates, sector classifications, earnings dates, news sentiment, chart-pattern recognition, or automated stop orders.
- It has no built-in walk-forward backtest, transaction-cost model, tax model, or delisting/survivorship-bias adjustment. Results should not be assumed to outperform QQQ, SPY, or a passive portfolio.
- `yfinance` data can be delayed, unavailable, corrected, or incomplete. A provider outage can fail the scan; the failure-email path exists for that reason.
- Relative-strength scores depend on the configured watchlist. A score of 90 means “strong relative to this configured universe under this formula,” not “90% probability of profit.”
- QQQ/SPY fallback remains equity exposure and can decline with the market. Diversification may reduce concentration risk but cannot eliminate market loss. [Investor.gov explains this limitation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).
- Review every recommendation in light of your own objectives, tax situation, IRA rules, liquidity needs, and risk tolerance. Consider a qualified financial professional for personalized advice.

## Security and privacy

- `holdings.txt` is personal portfolio input. Do not commit or publish it.
- Database, logs, generated site files, and distribution files are ignored by default.
- SMTP credentials are read only from environment variables: `EMAIL_SMTP_USER`, `EMAIL_SMTP_APP_PASSWORD`, `REPORT_TO_EMAIL`, and optional `REPORT_FROM_EMAIL`. Never add credentials to JSON, source code, logs, or generated output.
