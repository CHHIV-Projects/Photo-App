<#
.SYNOPSIS
Start Photo Organizer in production mode.

.DESCRIPTION
Starts the Photo Organizer stack with production configuration:
- Production database (photo_organizer_prod)
- NAS-backed storage paths
- No hot reload
- Production-safe startup sequence
- Requires .env.production configuration

.EXAMPLE
.\start_photo_organizer_prod.ps1

.NOTES
??? This is a v1.0 baseline script. Review and test before production use.
  Requires .env.production to be configured with NAS paths.
#>

param(
    [int]$HealthCheckTimeoutSeconds = 30,
    [int]$ServiceStartTimeoutSeconds = 60,
    [switch]$DryRun = $false
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$DockerDir = Join-Path $ProjectRoot "docker"
$LogsDir = Join-Path $ProjectRoot "storage" "logs" "runtime"
$EnvFile = Join-Path $BackendRoot ".env.production"

$LogFile = Join-Path $LogsDir "startup_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Service ports
$PostgresPort = 5432
$RedisPort = 6379
$BackendPort = 8001
$FrontendPort = 3000

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

function Write-Log {
    param($Message, $IsError = $false)
    if ($IsError) {
        $line = "[$((Get-Date).ToString('HH:mm:ss'))] ??? $Message"
        Write-Host $line -ForegroundColor Red
    } else {
        $line = "[$((Get-Date).ToString('HH:mm:ss'))] $Message"
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

function Test-PortOpen {
    param($Port, $Host = "127.0.0.1")
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($Host, $Port, $null, $null)
        $result.AsyncWaitHandle.WaitOne($HealthCheckTimeoutSeconds * 1000) | Out-Null
        if ($tcp.Connected) {
            $tcp.Close()
            return $true
        }
    } catch { }
    return $false
}

function Wait-ForPort {
    param($Port, $ServiceName, $TimeoutSeconds = 30)
    $elapsed = 0
    $interval = 1
    Write-Log "  ??? Waiting for $ServiceName on port $Port..."
    while ($elapsed -lt $TimeoutSeconds) {
        if (Test-PortOpen -Port $Port) {
            Write-Log "  ??? $ServiceName is ready (took ${elapsed}s)"
            return $true
        }
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    Write-Log "  ??? $ServiceName did not respond within ${TimeoutSeconds}s" -IsError $true
    return $false
}

function Test-CommandExists {
    param($Command)
    $result = $null
    try { $result = Get-Command $Command -ErrorAction Stop } catch { }
    return $null -ne $result
}

function Test-Path-Exists {
    param($Path, $PathType = "Any")
    if ($PathType -eq "File") {
        return [System.IO.File]::Exists($Path)
    } elseif ($PathType -eq "Directory") {
        return [System.IO.Directory]::Exists($Path)
    } else {
        return (Test-Path $Path)
    }
}

function Ensure-Directory {
    param($Path)
    if (-not (Test-Path $Path)) {
        Write-Log "  Creating directory: $Path"
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Yellow
Write-Host "  Photo Organizer Production Startup`n" -ForegroundColor Yellow
Write-Host "????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "  [DRY RUN MODE - No services will be started]`n" -ForegroundColor Yellow
}

# Create logs directory
Ensure-Directory -Path $LogsDir

Write-LogSection "Configuration"
Write-Log "Project root: $ProjectRoot"
Write-Log "Backend root: $BackendRoot"
Write-Log "Frontend root: $FrontendRoot"
Write-Log "Log file: $LogFile"
Write-Log "Environment: production"
Write-Log "Mode: $(if ($DryRun) { 'DRY RUN' } else { 'PRODUCTION' })"

# ==============================================================================
# PREFLIGHT CHECKS
# ==============================================================================

Write-LogSection "Preflight Checks"

# ??? Production config required
if (-not (Test-Path-Exists -Path $EnvFile -PathType "File")) {
    Write-Log "??? Production config file not found: $EnvFile" -IsError $true
    Write-Log "  Required: .env.production with production database and storage paths"
    Write-Log "  Refusing to start without explicit production configuration."
    exit 1
}
Write-Log "??? Config file found: $EnvFile"

# Parse .env.production to get storage paths (basic parsing)
Write-Log "  Parsing .env.production..."
$envContent = Get-Content $EnvFile
$vaultPath = $null
$logPath = $null

foreach ($line in $envContent) {
    if ($line -match '^VAULT_PATH=(.*)$') {
        $vaultPath = $matches[1].Trim()
    }
    if ($line -match '^LOGS_PATH=(.*)$') {
        $logPath = $matches[1].Trim()
    }
}

# ??? NAS paths must be reachable
if ($vaultPath) {
    Write-Log "  Vault path from config: $vaultPath"
    
    # Expand environment variables if present
    $vaultPath = [System.Environment]::ExpandEnvironmentVariables($vaultPath)
    
    if (Test-Path-Exists -Path $vaultPath -PathType "Directory") {
        Write-Log "  ??? Vault path is accessible"
    } else {
        Write-Log "  ??? Vault path is NOT accessible: $vaultPath" -IsError $true
        Write-Log "    If using NAS, ensure the share is mounted."
        Write-Log "    Example: net use Z: \\HENDERSON-NAS\PhotoOrganizer /persistent:yes"
        if (-not $DryRun) {
            exit 1
        }
    }
} else {
    Write-Log "  ??? VAULT_PATH not found in .env.production" -IsError $true
    if (-not $DryRun) {
        exit 1
    }
}

# Check if Docker is available
if (Test-CommandExists "docker") {
    Write-Log "??? Docker is available"
} else {
    Write-Log "??? Docker not found. Please install Docker Desktop for Windows." -IsError $true
    if (-not $DryRun) {
        exit 1
    }
}

# Check for port conflicts
$portConflicts = @()
foreach ($port in @($PostgresPort, $RedisPort, $BackendPort, $FrontendPort)) {
    if (Test-PortOpen -Port $port) {
        Write-Log "??? Port $port is already in use"
        $portConflicts += $port
    }
}

if ($portConflicts.Count -gt 0) {
    Write-Log "??? Port conflicts detected: $($portConflicts -join ', ')" -IsError $true
    Write-Log "  Existing services may still be running."
    if (-not $DryRun) {
        exit 1
    }
}
Write-Log "??? No port conflicts detected"

# ==============================================================================
# DRY RUN SUMMARY
# ==============================================================================

if ($DryRun) {
    Write-LogSection "Dry Run Summary"
    Write-Log "??? All preflight checks passed"
    Write-Log "??? Ready to start in production mode"
    Write-Log ""
    Write-Log "To start for real, run:"
    Write-Log "  .\start_photo_organizer_prod.ps1"
    Write-Log ""
    exit 0
}

# ==============================================================================
# START DOCKER SERVICES
# ==============================================================================

Write-LogSection "Docker Services"

Write-Log "Starting Docker services..."

Push-Location $DockerDir
try {
    # Start Docker Compose in background
    Write-Log "  ??? Starting PostgreSQL and Redis..."
    $dockerProcess = Start-Process -FilePath "docker-compose" -ArgumentList "up" -NoNewWindow -PassThru

    # Wait for services to be ready
    if (Wait-ForPort -Port $PostgresPort -ServiceName "PostgreSQL" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "??? PostgreSQL is ready"
    } else {
        Write-Log "??? PostgreSQL failed to start" -IsError $true
        Stop-Process -InputObject $dockerProcess -Force -ErrorAction SilentlyContinue
        exit 1
    }

    if (Wait-ForPort -Port $RedisPort -ServiceName "Redis" -TimeoutSeconds 15) {
        Write-Log "??? Redis is ready"
    } else {
        Write-Log "??? Redis failed to start" -IsError $true
        Stop-Process -InputObject $dockerProcess -Force -ErrorAction SilentlyContinue
        exit 1
    }
} finally {
    Pop-Location
}

# ==============================================================================
# START BACKEND
# ==============================================================================

Write-LogSection "Backend Service"

Push-Location $BackendRoot
try {
    Write-Log "Starting backend service..."

    # Production backend: no reload
    $uvicornArgs = @(
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", $BackendPort
    )

    Write-Log "  ??? Command: python -m uvicorn $($uvicornArgs -join ' ')"
    $backendProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn") + $uvicornArgs -NoNewWindow -PassThru

    if (Wait-ForPort -Port $BackendPort -ServiceName "Backend" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "??? Backend is ready"
    } else {
        Write-Log "??? Backend failed to start" -IsError $true
        Stop-Process -InputObject $backendProcess -Force -ErrorAction SilentlyContinue
        exit 1
    }
} finally {
    Pop-Location
}

# ==============================================================================
# START FRONTEND
# ==============================================================================

Write-LogSection "Frontend Service"

Push-Location $FrontendRoot
try {
    Write-Log "Starting frontend service..."
    Write-Log "  ??? Command: npm start (production mode)"

    # Production frontend uses 'start' which serves built version
    $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "start" -NoNewWindow -PassThru

    Start-Sleep -Seconds 3  # Wait for npm to start
    
    if (Test-PortOpen -Port $FrontendPort) {
        Write-Log "??? Frontend is ready"
    } else {
        Write-Log "??? Frontend may still be starting..."
    }
} finally {
    Pop-Location
}

# ==============================================================================
# FINAL STATUS
# ==============================================================================

Write-LogSection "Production Startup Complete"

$ready = $true
if (-not (Test-PortOpen -Port $PostgresPort)) { $ready = $false; Write-Log "  Database check failed" }
if (-not (Test-PortOpen -Port $RedisPort)) { $ready = $false; Write-Log "  Cache check failed" }
if (-not (Test-PortOpen -Port $BackendPort)) { $ready = $false; Write-Log "  Backend check failed" }
if (-not (Test-PortOpen -Port $FrontendPort)) { $ready = $false; Write-Log "  Frontend check failed" }

if ($ready) {
    Write-Host "??? All production services are running" -ForegroundColor Green
    Write-Log "??? All production services are running"
    
    Write-Host "`n???? Photo Organizer (PRODUCTION) is ready on http://127.0.0.1:$FrontendPort`n" -ForegroundColor Green
    Write-Log "Production instance ready"
    
    # Try to open browser
    try {
        Start-Process "http://127.0.0.1:$FrontendPort"
        Write-Log "??? Browser opened"
    } catch {
        Write-Log "??? Could not open browser automatically. Visit http://127.0.0.1:$FrontendPort manually."
    }
    
    Write-Host "`nTo stop all services, press Ctrl+C or run: .\stop_photo_organizer.ps1`n" -ForegroundColor Cyan
    Write-Log "Operator can stop with stop script or Ctrl+C"
    
    Write-Host "????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Yellow
    Write-Log "Production startup successful"
    
    Read-Host "Press Enter to continue (or Ctrl+C to stop)"
} else {
    Write-Host "??? Production startup failed. Check log file: $LogFile" -ForegroundColor Red
    Write-Log "??? Production startup failed" -IsError $true
    exit 1
}

