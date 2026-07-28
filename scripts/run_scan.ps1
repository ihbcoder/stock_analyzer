param(
    [string]$ProjectRoot = "C:\Users\k_buh\Code\stock_analyzer",
    [string]$InputFile = "stocks.json",
    [string]$OutputFile = "results.json",
    [string]$DatabaseFile = "data\stock_analyzer.db",
    [string]$LogFile = "logs\stock_analyzer.log",
    [string]$DashboardFile = "site\index.html"
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$inputPath = Join-Path $resolvedProjectRoot $InputFile
$outputPath = Join-Path $resolvedProjectRoot $OutputFile
$dbPath = Join-Path $resolvedProjectRoot $DatabaseFile
$logPath = Join-Path $resolvedProjectRoot $LogFile
$dashboardPath = Join-Path $resolvedProjectRoot $DashboardFile

Set-Location -LiteralPath $resolvedProjectRoot

& py main.py scan $inputPath --output $outputPath --db $dbPath --log $logPath --dashboard-output $dashboardPath
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    exit $exitCode
}

exit 0
