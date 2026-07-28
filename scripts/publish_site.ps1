param(
    [string]$ProjectRoot = "C:\Users\k_buh\Code\stock_analyzer",
    [string]$InputFile = "stocks.json",
    [string]$OutputFile = "results.json",
    [string]$DatabaseFile = "data\stock_analyzer.db",
    [string]$LogFile = "logs\stock_analyzer.log",
    [string]$DashboardFile = "site\index.html",
    [string]$DashboardDataFile = "site\dashboard-data.json",
    [string]$Remote = "origin",
    [string]$Branch = "main",
    [switch]$SkipCommit,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$scanScript = Join-Path $resolvedProjectRoot "scripts\run_scan.ps1"

Set-Location -LiteralPath $resolvedProjectRoot

& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $scanScript `
    -ProjectRoot $resolvedProjectRoot `
    -InputFile $InputFile `
    -OutputFile $OutputFile `
    -DatabaseFile $DatabaseFile `
    -LogFile $LogFile `
    -DashboardFile $DashboardFile

$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    exit $exitCode
}

$publishFiles = @(
    $OutputFile,
    $DashboardFile,
    $DashboardDataFile
)

& git add -f -- @publishFiles
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    exit $exitCode
}

& git diff --cached --quiet --exit-code
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "publish complete: no generated site changes"
    exit 0
}

if ($SkipCommit) {
    Write-Host "publish ready: generated files staged but not committed"
    exit 0
}

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
$commitMessage = "Publish dashboard update $timestamp"

& git commit -m $commitMessage
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    exit $exitCode
}

if ($SkipPush) {
    Write-Host "publish complete: committed locally"
    exit 0
}

& git push $Remote $Branch
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    exit $exitCode
}

Write-Host "publish complete: pushed $Remote/$Branch"
