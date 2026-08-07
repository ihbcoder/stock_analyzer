param(
    [string]$ProjectRoot = "C:\Users\k_buh\Code\stock_analyzer",
    [string]$InputFile = "stocks.json",
    [string]$OutputFile = "results.json",
    [string]$DatabaseFile = "data\stock_analyzer.db",
    [string]$LogFile = "logs\stock_analyzer.log",
    [string]$DashboardFile = "site\index.html",
    [string]$HoldingsFile = "holdings.txt",
    [switch]$EmailReport
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$inputPath = Join-Path $resolvedProjectRoot $InputFile
$outputPath = Join-Path $resolvedProjectRoot $OutputFile
$dbPath = Join-Path $resolvedProjectRoot $DatabaseFile
$logPath = Join-Path $resolvedProjectRoot $LogFile
$dashboardPath = Join-Path $resolvedProjectRoot $DashboardFile

Set-Location -LiteralPath $resolvedProjectRoot

$scanArgs = @(
    "main.py",
    "scan",
    $inputPath,
    "--output", $outputPath,
    "--db", $dbPath,
    "--log", $logPath,
    "--dashboard-output", $dashboardPath,
    "--holdings-file", (Join-Path $resolvedProjectRoot $HoldingsFile)
)

if ($EmailReport) {
    $scanArgs += "--email-report"
}

& py @scanArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    exit $exitCode
}

exit 0
