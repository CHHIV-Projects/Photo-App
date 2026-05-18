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
This is a v1.0 baseline script. Review and test before production use.
Requires .env.production to be configured with NAS paths.
Sets APP_RUNTIME_PROFILE=production before starting the backend.
Uses Docker Compose project name 'photo-organizer-prod' for volume separation.
#>

param(
    [int]$HealthCheckTimeoutSeconds = 30,
    [int]$ServiceStartTimeoutSeconds = 60,
    [switch]$DryRun = $false
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$DockerDir = Join-Path $ProjectRoot "docker"
$LogsDir = Join-Path (Join-Path (Join-Path $ProjectRoot "storage") "logs") "runtime"
$EnvFile = Join-Path $BackendRoot ".env.production"

$LogFile = Join-Path $LogsDir "startup_prod_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Prefer the workspace venv interpreter so runtime dependencies are consistent.
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# Docker Compose project name -- keeps prod volumes separate from development.
$DockerProject = "photo-organizer-prod"
$ProdDbName    = "photo_organizer_prod"

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
        $line = "[$((Get-Date).ToString('HH:mm:ss'))] [ERROR] $Message"
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
    param($Port, $HostAddress = "127.0.0.1")
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($HostAddress, $Port, $null, $null)
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
    Write-Log "  -> Waiting for $ServiceName on port $Port..."
    while ($elapsed -lt $TimeoutSeconds) {
        if (Test-PortOpen -Port $Port) {
            Write-Log "  [OK] $ServiceName is ready (took ${elapsed}s)"
            return $true
        }
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    Write-Log "  [ERROR] $ServiceName did not respond within ${TimeoutSeconds}s" -IsError $true
    return $false
}

function Wait-ForHttpEndpoint {
    param($Url, $ServiceName = "HTTP endpoint", $TimeoutSeconds = 30)
    $elapsed = 0
    $interval = 1
    Write-Log "  -> Waiting for $ServiceName at $Url..."
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Log "  [OK] $ServiceName is ready (took ${elapsed}s)"
                return $true
            }
        } catch { }
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    Write-Log "  [ERROR] $ServiceName did not return HTTP 200 within ${TimeoutSeconds}s" -IsError $true
    return $false
}

function Test-CommandExists {
    param($Command)
    $result = $null
    try { $result = Get-Command $Command -ErrorAction Stop } catch { }
    return $null -ne $result
}

function Wait-ForDockerDaemon {
    param($TimeoutSeconds = 90)
    $elapsed = 0
    $interval = 2
    while ($elapsed -lt $TimeoutSeconds) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    return $false
}

function Ensure-DockerReady {
    if (-not (Test-CommandExists "docker")) {
        Write-Log "Docker CLI not found. Please install Docker Desktop for Windows." -IsError $true
        return $false
    }

    if (Wait-ForDockerDaemon -TimeoutSeconds 5) {
        return $true
    }

    Write-Log "Docker daemon is not running. Attempting to start Docker Desktop..." -IsError $true
    $dockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopExe) {
        try {
            Start-Process -FilePath $dockerDesktopExe | Out-Null
        } catch {
            Write-Log "Failed to launch Docker Desktop: $_" -IsError $true
            return $false
        }
    } else {
        Write-Log "Docker Desktop executable not found at: $dockerDesktopExe" -IsError $true
        return $false
    }

    Write-Log "  -> Waiting for Docker daemon to become ready..."
    if (-not (Wait-ForDockerDaemon -TimeoutSeconds 90)) {
        Write-Log "Docker daemon did not become ready in time." -IsError $true
        Write-Log "  Open Docker Desktop and wait until it shows 'Engine running', then retry."
        return $false
    }

    Write-Log "[OK] Docker daemon is ready"
    return $true
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

Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "  Photo Organizer - Production Startup" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "  [DRY RUN MODE - No services will be started]`n" -ForegroundColor Yellow
}

# Create logs directory
Ensure-Directory -Path $LogsDir

Write-LogSection "Configuration"
Write-Log "Project root  : $ProjectRoot"
Write-Log "Backend root  : $BackendRoot"
Write-Log "Frontend root : $FrontendRoot"
Write-Log "Log file      : $LogFile"
Write-Log "Profile       : production"
Write-Log "Docker project: $DockerProject"
Write-Log "Prod DB name  : $ProdDbName"
Write-Log "Python exe    : $PythonExe"
Write-Log "Mode          : $(if ($DryRun) { 'DRY RUN' } else { 'PRODUCTION' })"

# ==============================================================================
# PREFLIGHT CHECKS
# ==============================================================================

Write-LogSection "Preflight Checks"

# Production config required -- no fallback.
if (-not (Test-Path-Exists -Path $EnvFile -PathType "File")) {
    Write-Log "Production config file not found: $EnvFile" -IsError $true
    Write-Log "  Required: .env.production with production database and storage paths"
    Write-Log "  Refusing to start without explicit production configuration."
    exit 1
}
Write-Log "[OK] Config file found: $EnvFile"

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

# NAS / Vault path check
if ($vaultPath) {
    Write-Log "  Vault path from config: $vaultPath"
    
    # Expand environment variables if present
    $vaultPath = [System.Environment]::ExpandEnvironmentVariables($vaultPath)
    
    if (Test-Path-Exists -Path $vaultPath -PathType "Directory") {
        Write-Log "  [OK] Vault path is accessible"
    } else {
        Write-Log "  Vault path is NOT accessible: $vaultPath" -IsError $true
        Write-Log "    If using NAS, ensure the share is mounted."
        Write-Log "    Example: net use Z: \\SERVER\Share /persistent:yes"
        if (-not $DryRun) {
            exit 1
        }
    }
} else {
    Write-Log "  VAULT_PATH not set in .env.production" -IsError $true
    if (-not $DryRun) {
        exit 1
    }
}

# Check if Docker is available
if (Ensure-DockerReady) {
    Write-Log "[OK] Docker is available"
} else {
    Write-Log "Docker is not ready." -IsError $true
    if (-not $DryRun) {
        exit 1
    }
}

# Check for port conflicts
$portConflicts = @()
foreach ($port in @($PostgresPort, $RedisPort, $BackendPort, $FrontendPort)) {
    if (Test-PortOpen -Port $port) {
        $portConflicts += $port
    }
}

if ($portConflicts.Count -gt 0) {
    Write-Log "Port conflicts on: $($portConflicts -join ', ')" -IsError $true
    Write-Log "  Existing services may still be running."
    if (-not $DryRun) {
        exit 1
    }
}
Write-Log "[OK] No port conflicts detected"

# ==============================================================================
# DRY RUN SUMMARY
# ==============================================================================

if ($DryRun) {
    Write-LogSection "Dry Run Summary"
    Write-Log "[OK] All preflight checks passed"
    Write-Log "[OK] Ready to start in production mode"
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

Write-Log "Starting Docker services (project: $DockerProject, DB: $ProdDbName)..."

# Set production DB name so docker-compose uses the correct database.
$env:APP_RUNTIME_PROFILE = "production"
$env:POSTGRES_DB         = $ProdDbName

Push-Location $DockerDir
try {
    # Use 'docker compose' (v2) with explicit project name for volume separation.
    $dockerProcess = Start-Process -FilePath "docker" -ArgumentList @("compose", "--project-name", $DockerProject, "up", "-d") -NoNewWindow -PassThru -Wait
    if ($dockerProcess.ExitCode -ne 0) {
        Write-Log "Docker compose failed to start services (exit code $($dockerProcess.ExitCode))." -IsError $true
        Write-Log "  Ensure Docker Desktop is open and engine is running, then retry."
        exit 1
    }

    # Wait for services to be ready
    if (Wait-ForPort -Port $PostgresPort -ServiceName "PostgreSQL" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "[OK] PostgreSQL is ready"
    } else {
        Write-Log "PostgreSQL failed to start" -IsError $true
        exit 1
    }

    if (Wait-ForPort -Port $RedisPort -ServiceName "Redis" -TimeoutSeconds 15) {
        Write-Log "[OK] Redis is ready"
    } else {
        Write-Log "Redis failed to start" -IsError $true
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

    Write-Log "  -> Command: $PythonExe -m uvicorn $($uvicornArgs -join ' ')"
    $backendArgList = @("-m", "uvicorn") + $uvicornArgs
    $backendProcess = Start-Process -FilePath $PythonExe -ArgumentList $backendArgList -NoNewWindow -PassThru

    if (Wait-ForPort -Port $BackendPort -ServiceName "Backend" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        $backendHealthUrl = "http://127.0.0.1:$BackendPort/health"
        if (Wait-ForHttpEndpoint -Url $backendHealthUrl -ServiceName "Backend health" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
            Write-Log "[OK] Backend is ready"
        } else {
            Write-Log "Backend health check failed" -IsError $true
            Stop-Process -InputObject $backendProcess -Force -ErrorAction SilentlyContinue
            exit 1
        }
    } else {
        Write-Log "Backend failed to start" -IsError $true
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
    Write-Log "  -> Command: npm start (production mode)"

    # Production frontend uses 'start' which serves built version
    # On Windows, npm should be launched via npm.cmd when using Start-Process.
    $frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "start" -NoNewWindow -PassThru

    if (Wait-ForPort -Port $FrontendPort -ServiceName "Frontend" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "[OK] Frontend is ready"
    } else {
        Write-Log "[WARN] Frontend may still be starting -- check port $FrontendPort"
    }
} finally {
    Pop-Location
}

# ==============================================================================
# FINAL STATUS
# ==============================================================================

Write-LogSection "Production Startup Complete"

$ready = $true
if (-not (Test-PortOpen -Port $PostgresPort)) { $ready = $false; Write-Log "  [ERROR] Database check failed" }
if (-not (Test-PortOpen -Port $RedisPort))    { $ready = $false; Write-Log "  [ERROR] Cache check failed" }
if (-not (Test-PortOpen -Port $BackendPort))  { $ready = $false; Write-Log "  [ERROR] Backend check failed" }
if (-not (Test-PortOpen -Port $FrontendPort)) { Write-Log "  [WARN] Frontend not responding on port $FrontendPort" }

if ($ready) {
    Write-Host "`n[OK] All production services are running" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend : http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
    Write-Host "  Backend  : http://127.0.0.1:$BackendPort" -ForegroundColor Cyan
    Write-Host "  Health   : http://127.0.0.1:$BackendPort/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Log "[OK] Production instance ready"

    # Try to open browser
    try {
        Start-Process "http://127.0.0.1:$FrontendPort"
        Write-Log "Browser opened"
    } catch {
        Write-Log "Could not open browser automatically. Visit http://127.0.0.1:$FrontendPort manually."
    }

    Write-Host "To stop all services run: .\stop_photo_organizer.ps1`n" -ForegroundColor Cyan
    Write-Log "Production startup successful."

    Read-Host "Press Enter to stop all services and exit"
    Write-Log "Shutdown requested from launcher prompt"
    & (Join-Path $PSScriptRoot "stop_photo_organizer.ps1") -FrontendPid $frontendProcess.Id -BackendPid $backendProcess.Id | Out-Null
    Write-Log "Launcher exit complete"
} else {
    Write-Host "`n[ERROR] Production startup failed. Check log: $LogFile" -ForegroundColor Red
    Write-Log "Production startup failed" -IsError $true
    exit 1
}

