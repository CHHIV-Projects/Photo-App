<#
.SYNOPSIS
Bootstrap production storage directories for Photo Organizer.

.DESCRIPTION
Validates and creates required production storage directories.
Reads configured paths from backend/.env.production.

Safe operations only:
- Checks whether required paths exist
- Creates missing local runtime directories
- Verifies write access where needed
- Writes a bootstrap log
- Fails clearly if NAS-backed Vault root is unavailable

This script does NOT:
- Delete or move any files
- Modify Vault or iCloud contents
- Ingest media
- Alter database records
- Fall back to development paths

.PARAMETER DryRun
Run all checks and report results without creating any directories.

.EXAMPLE
.\bootstrap_production_storage.ps1 -DryRun
.\bootstrap_production_storage.ps1

.NOTES
Requires backend/.env.production to exist.
NAS paths must be accessible when this script runs.
#>

param(
    [switch]$DryRun = $false
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendRoot   = Join-Path $ProjectRoot "backend"
$EnvFile       = Join-Path $BackendRoot ".env.production"
$LogsDir       = Join-Path (Join-Path (Join-Path $ProjectRoot "storage") "logs") "runtime"
$LogFile       = Join-Path $LogsDir "bootstrap_prod_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

function Write-Log {
    param($Message, $IsError = $false)
    $ts   = (Get-Date).ToString("HH:mm:ss")
    $line = "[$ts] $Message"
    if ($IsError) {
        Write-Host $line -ForegroundColor Red
    } else {
        Write-Host $line
    }
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

function Write-LogSection {
    param($Title)
    $line = "--- $Title ---"
    Write-Host "`n$line" -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value "`n$line" -ErrorAction SilentlyContinue
}

function Read-EnvFile {
    param($Path)
    $values = @{}
    if (-not (Test-Path $Path)) { return $values }
    foreach ($line in (Get-Content $Path)) {
        $line = $line.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { continue }
        if ($line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            $values[$key] = [System.Environment]::ExpandEnvironmentVariables($val)
        }
    }
    return $values
}

function Test-WriteAccess {
    param($DirPath)
    $testFile = Join-Path $DirPath ".write_test_$(Get-Random)"
    try {
        [System.IO.File]::WriteAllText($testFile, "write_test")
        Remove-Item $testFile -Force -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

function Ensure-Directory {
    param($Path, $Label)
    if ($DryRun) {
        if (Test-Path $Path) {
            Write-Log "  [OK] $Label exists: $Path"
        } else {
            Write-Log "  [DRY RUN] Would create: $Path"
        }
        return $true
    }
    if (Test-Path $Path) {
        Write-Log "  [OK] $Label exists: $Path"
        return $true
    }
    try {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Log "  [CREATED] ${Label}: $Path"
        return $true
    } catch {
        Write-Log "  [ERROR] Failed to create $Label at $Path -- $_" -IsError $true
        return $false
    }
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "  Photo Organizer - Production Storage Bootstrap" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "  [DRY RUN MODE - No directories will be created]`n" -ForegroundColor Yellow
}

# Ensure local log directory exists before writing log
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-LogSection "Environment"
Write-Log "Project root : $ProjectRoot"
Write-Log "Env file     : $EnvFile"
Write-Log "Log file     : $LogFile"
Write-Log "Mode         : $(if ($DryRun) { 'DRY RUN' } else { 'LIVE' })"

# ==============================================================================
# REQUIRE PRODUCTION CONFIG
# ==============================================================================

Write-LogSection "Production Config"

if (-not (Test-Path $EnvFile)) {
    Write-Log "[ERROR] Production config not found: $EnvFile" -IsError $true
    Write-Log "  Create backend/.env.production from the template:"
    Write-Log "    copy backend\.env.production.example backend\.env.production"
    Write-Log "  Then fill in real paths and credentials."
    exit 1
}
Write-Log "[OK] Found: $EnvFile"

$env = Read-EnvFile -Path $EnvFile
Write-Log "[OK] Parsed production config ($($env.Count) variables)"

# Verify this is a production config
$profileVal = $env["APP_RUNTIME_PROFILE"]
if ($profileVal -and $profileVal -ne "production") {
    Write-Log "[ERROR] APP_RUNTIME_PROFILE in config is '$profileVal', expected 'production'" -IsError $true
    Write-Log "  This script must only be run with a production config."
    exit 1
}

# ==============================================================================
# NAS / VAULT PATH CHECK (REQUIRED)
# ==============================================================================

Write-LogSection "NAS / Vault Path"

$vaultPath = $env["VAULT_PATH"]
if (-not $vaultPath) {
    Write-Log "[ERROR] VAULT_PATH is not set in .env.production" -IsError $true
    exit 1
}

Write-Log "  Vault path : $vaultPath"

if (Test-Path $vaultPath) {
    Write-Log "[OK] Vault path is accessible"
    if (-not $DryRun) {
        if (Test-WriteAccess -DirPath $vaultPath) {
            Write-Log "[OK] Vault path is writable"
        } else {
            Write-Log "[WARN] Vault path exists but write test failed -- check permissions"
        }
    }
} else {
    Write-Log "[ERROR] Vault path is NOT accessible: $vaultPath" -IsError $true
    Write-Log "  If using NAS, ensure the share is mounted before running this script."
    Write-Log "  Example: net use Z: \\SERVER\Share /persistent:yes"
    if (-not $DryRun) {
        exit 1
    }
}

# ==============================================================================
# LOCAL STORAGE DIRECTORIES
# ==============================================================================

Write-LogSection "Local Storage Directories"

$errors = 0

# Determine local storage root
$storageRoot = $env["STORAGE_ROOT"]
if (-not $storageRoot) {
    Write-Log "[WARN] STORAGE_ROOT not set -- using project-relative default"
    $storageRoot = Join-Path $ProjectRoot "storage"
}
Write-Log "  Storage root: $storageRoot"

# Required local directories with config key overrides
$localDirs = [ordered]@{
    "Drop Zone"   = if ($env["DROP_ZONE_PATH"])    { $env["DROP_ZONE_PATH"] }    else { Join-Path $storageRoot "drop_zone" }
    "Quarantine"  = if ($env["QUARANTINE_PATH"])   { $env["QUARANTINE_PATH"] }   else { Join-Path $storageRoot "quarantine" }
    "Previews"    = if ($env["PREVIEWS_PATH"])      { $env["PREVIEWS_PATH"] }      else { Join-Path $storageRoot "previews" }
    "Thumbnails"  = if ($env["THUMBNAILS_PATH"])    { $env["THUMBNAILS_PATH"] }    else { Join-Path $storageRoot "thumbnails" }
    "Review"      = if ($env["REVIEW_PATH"])        { $env["REVIEW_PATH"] }        else { Join-Path $storageRoot "review" }
    "Logs"        = if ($env["LOGS_PATH"])          { $env["LOGS_PATH"] }          else { Join-Path $storageRoot "logs" }
    "Logs/Runtime"= Join-Path (if ($env["LOGS_PATH"]) { $env["LOGS_PATH"] } else { Join-Path $storageRoot "logs" }) "runtime"
    "Reports"     = if ($env["REPORTS_PATH"])       { $env["REPORTS_PATH"] }       else { Join-Path $storageRoot "reports" }
}

foreach ($entry in $localDirs.GetEnumerator()) {
    $ok = Ensure-Directory -Path $entry.Value -Label $entry.Key
    if (-not $ok) { $errors++ }
}

# ==============================================================================
# NAS-BACKED DIRECTORIES (NON-VAULT)
# ==============================================================================

Write-LogSection "NAS-Backed Directories"

$nasDirs = [ordered]@{
    "Exports/iCloud" = $env["EXPORTS_ICLOUD_PATH"]
}

foreach ($entry in $nasDirs.GetEnumerator()) {
    if ($entry.Value) {
        if (Test-Path (Split-Path $entry.Value -Parent) -ErrorAction SilentlyContinue) {
            $ok = Ensure-Directory -Path $entry.Value -Label $entry.Key
            if (-not $ok) { $errors++ }
        } else {
            Write-Log "  [WARN] Parent of $($entry.Key) not accessible -- skipping: $($entry.Value)"
        }
    } else {
        Write-Log "  [SKIP] $($entry.Key) not configured in .env.production"
    }
}

# ==============================================================================
# BACKUP PLACEHOLDER DIRECTORIES
# ==============================================================================

Write-LogSection "Backup Directories"

Write-Log "  NOTE: Backup automation is deferred to a later milestone."
Write-Log "  Production DB backups should target NAS when implemented."
Write-Log "  Recommended target: <NAS_ROOT>\backups\postgres"

# ==============================================================================
# SUMMARY
# ==============================================================================

Write-LogSection "Bootstrap Summary"

if ($errors -gt 0) {
    Write-Log "[ERROR] Bootstrap completed with $errors error(s). Review output above." -IsError $true
    Write-Log "  Log: $LogFile"
    exit 1
} else {
    if ($DryRun) {
        Write-Host "`n[OK] Dry run complete -- all checks passed. Run without -DryRun to create directories.`n" -ForegroundColor Green
    } else {
        Write-Host "`n[OK] Production storage bootstrap complete.`n" -ForegroundColor Green
    }
    Write-Log "[OK] Bootstrap complete. Log: $LogFile"
    exit 0
}
