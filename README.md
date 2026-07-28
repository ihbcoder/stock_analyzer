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

## Input format

See [stocks.json](./stocks.json).

For after-close runs, use [stocks_eod.json](./stocks_eod.json). It uses the same watchlist with `market_hours_only` set to `false`.

## Notes

- v1 uses JSON only.
- The provider layer is isolated so you can swap in Alpaca, Twelve Data, or another source later.
- Scoring is deliberately simple and transparent.
- SQLite is built in through Python's standard library. Each run is saved in `analysis_runs` and each ranked stock row is saved in `stock_rankings`.
- The CLI keeps the old `python main.py stocks.json ...` flow working by treating it as `scan`.
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
