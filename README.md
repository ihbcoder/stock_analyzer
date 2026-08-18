# stock_analyzer

Minimal momentum stock scanner scaffold.

Current scope:

- read a JSON stock list
- fetch recent OHLCV data through a provider interface
- calculate momentum indicators
- score and rank stocks
- write a JSON results file
- persist scan runs and rankings to SQLite
- optionally skip scans outside regular NYSE market hours
- write rotating log files for scheduler-friendly operation
- generate a static HTML dashboard from the latest saved run

Default provider: `yfinance`

This is a research scaffold, not a trading system.

## Quick start

1. Create a virtual environment.
2. Install requirements.
3. Run:

```bash
python main.py stocks.json --output results.json
```

With an explicit database path:

```bash
python main.py stocks.json --output results.json --db data/stock_analyzer.db
```

Show recent saved runs and the latest rankings:

```bash
python main.py report --db data/stock_analyzer.db
```

Build a monthly rebalance recommendation from the latest two saved runs and a holdings file:

```bash
python main.py rebalance --db data/stock_analyzer.db --holdings-file holdings_example.txt
```

Filter the latest saved rankings by signal:

```bash
python main.py report --db data/stock_analyzer.db --signal STRONG --top 5
```

Write logs to a specific file:

```bash
python main.py scan stocks.json --log logs/stock_analyzer.log
```

Generate the dashboard explicitly to the default location:

```bash
python main.py scan stocks.json --dashboard-output site/index.html
```

To show monthly rebalance recommendations in the generated web pages, add a `holdings.txt` file in the project root with one ticker per line. If `holdings.txt` is missing, the pages fall back to `holdings_example.txt` and label it as sample data.

Serve the generated dashboard locally:

```bash
python main.py serve --site-dir site --host 127.0.0.1 --port 8000
```

Build a deployment-ready static bundle for hosting providers that expect a Node build:

```bash
node build-site.mjs
```

Run a scan, regenerate the dashboard, commit the generated files, and push them for hosted publishing:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_site.ps1
```

Send a daily email after the scan using local SMTP environment variables:

```powershell
py main.py scan stocks.json --output results.json --db data/stock_analyzer.db --dashboard-output site/index.html --email-report
```

## Input format

See [stocks.json](./stocks.json).

For after-close runs, use [stocks_eod.json](./stocks_eod.json). It uses the same watchlist with `market_hours_only` set to `false`.

## Notes

- v1 uses JSON only.
- The provider layer is isolated so you can swap in Alpaca, Twelve Data, or another source later.
- The monthly momentum model (`monthly_momentum_v2`) ranks 3-, 6-, and 12-month excess returns versus QQQ across the watchlist, uses one-month relative strength as a smaller acceleration input, and uses the 50/200-day trends plus 52-week-high proximity as confirmation. RSI remains an extension flag, not a score input.
- Each scan records its scoring version. Rebalance comparisons only use runs with the current scoring version, so pre-v2 scores are retained for history but never influence v2 momentum changes or recommendations.
- Monthly rebalance targets use up to eight qualified stocks. When fewer names qualify, the remaining allocation is invested 50/50 in QQQ and SPY rather than held as cash. A weak QQQ regime (below its 200-day average or above the configured 20-day volatility limit) blocks new individual-stock buys and routes unused target weight to that fallback.
- New stock purchases require at least $10 million of 20-day average dollar volume by default. Change `agent.minimum_average_dollar_volume` in the watchlist JSON if needed.
- Input files must be `stocks.json` or `stocks_eod.json`; generated `results*.json` files cannot be used as watchlists.
- SQLite is built in through Python's standard library. Each run is saved in `analysis_runs` and each ranked stock row is saved in `stock_rankings`.
- The CLI keeps the old `python main.py stocks.json ...` flow working by treating it as `scan`.
- `--email-report` sends the latest scan summary through SMTP. If the scan fails before it can produce rankings, it instead sends a `FAILED` report with the error message; the command still exits non-zero so Task Scheduler records the failure. The email includes both plain-text and HTML versions. By default it assumes Gmail SMTP (`smtp.gmail.com:465`), but you can override the host and port with environment variables.
- Email credentials stay local. Set `EMAIL_SMTP_USER`, `EMAIL_SMTP_APP_PASSWORD`, and `REPORT_TO_EMAIL` on the machine before using `--email-report`. `REPORT_FROM_EMAIL` is optional and defaults to the SMTP user.
- `REPORT_TO_EMAIL` can contain multiple recipients separated by commas or semicolons, for example: `yourgmail@gmail.com;k_buhagiar@yahoo.com`.
- `python main.py rebalance` builds a monthly keep/sell/buy report from v2 scans only, targeting the current holdings count by default. It has a one-run grace period and a default 10-point rotation gap for names that just fell out of the top group. Override the target count with `--top-n` or the gap with `--rotation-score-gap`.
- When `agent.market_hours_only` is `true`, scans are skipped when the NYSE is closed, including market holidays. The saved run is marked `skipped_market_closed`.
- Use `stocks.json` for intraday scans and `stocks_eod.json` for end-of-day or evening runs.
- The CLI writes rotating logs by default to `logs/stock_analyzer.log`.
- Each scan refreshes a static dashboard at `site/index.html` by default.
- Each scan also writes `site/dashboard-data.json` for static hosting and browser-side filtering.
- The local server uses only Python's standard library.
- `package.json` and `build-site.mjs` provide a minimal static build path that copies `site/` into `dist/` for hosted deployment.
- `.github/workflows/deploy-pages.yml` deploys the tracked `site/` output to GitHub Pages on each push to `main` that changes `site/`.
- GitHub Pages requires a one-time repository setting change: in GitHub, open `Settings` -> `Pages` and set `Source` to `GitHub Actions`.
- `scripts/publish_site.ps1` is the unattended publish entry point for Task Scheduler. It stages only generated output files: `results.json`, `site/index.html`, and `site/dashboard-data.json`.
- For Windows scheduling details, see [TASK_SCHEDULER.md](./TASK_SCHEDULER.md).
