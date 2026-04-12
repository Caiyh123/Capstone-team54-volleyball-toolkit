# Scheduled sync: all ETL sources (Python orchestrator).
# Task Scheduler example:
#   powershell.exe -ExecutionPolicy Bypass -File "D:\...\Capstone-team54-volleyball-toolkit\scripts\run_scheduled_sync.ps1"
#
# Needs: Python on PATH (or edit script to use full path to python.exe), .env in repo root
#        (CATAPULT_*, GYMAWARE_*, DATABASE_URL, VALD_*, WHOOP_* as needed).
# Optional: GYMAWARE_USE_ALLOWLIST=1 + allowlist workbook; SCHEDULED_* lookback env vars.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$LogDir = Join-Path $Root "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir ("sync_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format "o"), $msg
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

Write-Log "START scheduled_etl.py --all root=$Root"

try {
    python scheduled_etl.py --all 2>&1 | Tee-Object -FilePath $Log -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Log "FAIL: scheduled_etl.py exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Log "DONE scheduled sync"
} catch {
    Write-Log "FAIL: $_"
    exit 1
}
