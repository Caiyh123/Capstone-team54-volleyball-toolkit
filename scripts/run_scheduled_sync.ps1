# Scheduled sync: Catapult + GymAware -> Supabase (add steps when more sources exist).
# Task Scheduler example:
#   powershell.exe -ExecutionPolicy Bypass -File "D:\...\Capstone-team54-volleyball-toolkit\scripts\run_scheduled_sync.ps1"
#
# Needs: Python on PATH (or edit script to use full path to python.exe), .env in repo root
#        (CATAPULT_*, GYMAWARE_*, DATABASE_URL). Optional: GYMAWARE_USE_ALLOWLIST=1 + allowlist workbook.

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

Write-Log "START scheduled sync root=$Root"

try {
    Write-Log "Catapult bulk_export..."
    python bulk_export.py 2>&1 | Tee-Object -FilePath $Log -Append
    Write-Log "Catapult upload_to_supabase..."
    python upload_to_supabase.py 2>&1 | Tee-Object -FilePath $Log -Append
    Write-Log "GymAware export..."
    python gymaware_export.py 2>&1 | Tee-Object -FilePath $Log -Append
    Write-Log "GymAware upload..."
    python upload_gymaware_to_supabase.py 2>&1 | Tee-Object -FilePath $Log -Append
    Write-Log "DONE scheduled sync"
} catch {
    Write-Log "FAIL: $_"
    exit 1
}
