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

## Input format

See [stocks.json](./stocks.json).

## Notes

- v1 uses JSON only.
- The provider layer is isolated so you can swap in Alpaca, Twelve Data, or another source later.
- Scoring is deliberately simple and transparent.
- SQLite is built in through Python's standard library. Each run is saved in `analysis_runs` and each ranked stock row is saved in `stock_rankings`.
- The CLI keeps the old `python main.py stocks.json ...` flow working by treating it as `scan`.
- When `agent.market_hours_only` is `true`, scans are skipped when the NYSE is closed, including market holidays. The saved run is marked `skipped_market_closed`.
- The CLI writes rotating logs by default to `logs/stock_analyzer.log`.
- Each scan refreshes a static dashboard at `site/index.html` by default.
- Each scan also writes `site/dashboard-data.json` for static hosting and browser-side filtering.
- The local server uses only Python's standard library.
- `package.json` and `build-site.mjs` provide a minimal static build path that copies `site/` into `dist/` for hosted deployment.
- For Windows scheduling details, see [TASK_SCHEDULER.md](./TASK_SCHEDULER.md).
