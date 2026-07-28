# Task Scheduler setup

Use the PowerShell wrapper so the scheduled task only has one stable command to run.

## Files used

- Script: `C:\Users\k_buh\Code\stock_analyzer\scripts\run_scan.ps1`
- Publish script: `C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1`
- Config: `C:\Users\k_buh\Code\stock_analyzer\stocks.json`
- End-of-day config: `C:\Users\k_buh\Code\stock_analyzer\stocks_eod.json`
- Database: `C:\Users\k_buh\Code\stock_analyzer\data\stock_analyzer.db`
- Log file: `C:\Users\k_buh\Code\stock_analyzer\logs\stock_analyzer.log`
- Dashboard: `C:\Users\k_buh\Code\stock_analyzer\site\index.html`

## One-time prerequisites

Install dependencies:

```powershell
cd C:\Users\k_buh\Code\stock_analyzer
py -m pip install -r requirements.txt
```

Run one manual scan first:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\k_buh\Code\stock_analyzer\scripts\run_scan.ps1
```

If you want the public web page to update automatically after each run, first configure GitHub Pages once in the repository:

- GitHub -> `stock_analyzer` -> `Settings` -> `Pages`
- Under `Build and deployment`, set `Source` to `GitHub Actions`

Then test one manual publish:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1
```

To test the end-of-day variant manually:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1 -InputFile stocks_eod.json
```

## Recommended hourly task

Create a task named `StockAnalyzerHourly`.

### General tab

- Name: `StockAnalyzerHourly`
- Description: `Run momentum stock scan every hour`
- Select: `Run whether user is logged on or not`
- Select: `Run with highest privileges`
- Configure for: `Windows 10` or `Windows 11`

### Triggers tab

Add trigger:

- Begin the task: `On a schedule`
- Settings: `Daily`
- Start: `9:35:00 AM`
- Recur every: `1 days`
- Advanced settings:
  - Repeat task every: `1 hour`
  - For a duration of: `8 hours`
  - Enabled: `checked`

This covers 9:35 AM through 4:35 PM Eastern. The code itself skips when the market is closed, so occasional off-hours runs are safe.

Use `stocks.json` for this task so `market_hours_only` stays enabled.

### Actions tab

Add action:

- Action: `Start a program`
- Program/script:

```text
powershell.exe
```

- Add arguments:

```text
-NoProfile -ExecutionPolicy Bypass -File "C:\Users\k_buh\Code\stock_analyzer\scripts\run_scan.ps1"
```

- Start in:

```text
C:\Users\k_buh\Code\stock_analyzer
```

If you want hosted publishing instead of local-only dashboard refresh, use this action instead:

- Program/script:

```text
powershell.exe
```

- Add arguments:

```text
-NoProfile -ExecutionPolicy Bypass -File "C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1"
```

- Start in:

```text
C:\Users\k_buh\Code\stock_analyzer
```

### Conditions tab

- Uncheck: `Start the task only if the computer is on AC power` if this machine is not a laptop
- Uncheck: `Stop if the computer switches to battery power` if not relevant
- Uncheck: `Start the task only if the computer is idle`
- Check: `Wake the computer to run this task` if the PC may sleep

### Settings tab

- Check: `Allow task to be run on demand`
- Check: `Run task as soon as possible after a scheduled start is missed`
- Check: `If the task fails, restart every`
  - every: `15 minutes`
  - attempt to restart up to: `3 times`
- If the task is already running:
  - select: `Do not start a new instance`

## Useful companion tasks

### Pre-market daily scan

If you want a once-daily pre-market run:

- Start time: `8:30 AM`
- Repeat: none

This will still skip if `market_hours_only` is true. Use this only if you later set that flag to false.

### End-of-day scan

If you want one run after the close:

- Start time: `4:10 PM`
- Repeat: none

Use `stocks_eod.json` for this task. It sets `market_hours_only` to `false`, so the run is allowed after the market closes and will use the most recent available data.

If you want this run to publish the hosted dashboard, use:

- Program/script:

```text
powershell.exe
```

- Add arguments:

```text
-NoProfile -ExecutionPolicy Bypass -File "C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1" -InputFile stocks_eod.json
```

- Start in:

```text
C:\Users\k_buh\Code\stock_analyzer
```

## Command-line creation alternative

You can also create the hourly task from an elevated PowerShell window:

```powershell
schtasks /Create /TN "StockAnalyzerHourly" /SC DAILY /ST 09:35 /RI 60 /DU 08:00 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\k_buh\Code\stock_analyzer\scripts\run_scan.ps1\"" /RL HIGHEST /F
```

Create the end-of-day publish task from an elevated PowerShell window:

```powershell
schtasks /Create /TN "StockAnalyzerEndOfDay" /SC DAILY /ST 16:10 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\k_buh\Code\stock_analyzer\scripts\publish_site.ps1\" -InputFile stocks_eod.json" /RL HIGHEST /F
```

## Verification

After the task runs, check:

- Task Scheduler history for return code
- `C:\Users\k_buh\Code\stock_analyzer\logs\stock_analyzer.log`
- `C:\Users\k_buh\Code\stock_analyzer\results.json`
- `C:\Users\k_buh\Code\stock_analyzer\data\stock_analyzer.db`
- `C:\Users\k_buh\Code\stock_analyzer\site\index.html`
- latest commit on `main` contains updated generated output files
- GitHub Actions shows a successful `Deploy dashboard to GitHub Pages` run if you used `publish_site.ps1`
- end-of-day runs should use `stocks_eod.json`, not `stocks.json`

Successful runs write a line like:

```text
Completed scan run_id=12 run_status=success rankings=15 generated_at=...
```

Skipped runs due to market hours write:

```text
Completed scan run_id=13 run_status=skipped_market_closed rankings=0 generated_at=...
```
