<#
.SYNOPSIS
Start Photo Organizer in development mode.

.DESCRIPTION
Starts the Photo Organizer stack with development configuration:
- Development database (photo_organizer_dev)
- Local storage paths (../storage/*)
- Hot reload enabled
- Development console output

.EXAMPLE
.\start_photo_organizer_dev.ps1

.NOTES
This is a v1.0 baseline script. Review before production use.
#>

param(
    [switch]$NoReload = $false,
    [int]$HealthCheckTimeoutSeconds = 30,
    [int]$ServiceStartTimeoutSeconds = 60
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$DockerDir = Join-Path $ProjectRoot "docker"
$LogsDir = Join-Path $ProjectRoot "storage" "logs" "runtime"
$EnvFile = Join-Path $BackendRoot ".env.development"

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
    param($Message)
    $line = "[$((Get-Date).ToString('HH:mm:ss'))] $Message"
    Write-Host $line
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
    Write-Log "  ??? $ServiceName did not respond within ${TimeoutSeconds}s"
    return $false
}

function Test-CommandExists {
    param($Command)
    $result = $null
    try { $result = Get-Command $Command -ErrorAction Stop } catch { }
    return $null -ne $result
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Green
Write-Host "  Photo Organizer Development Startup`n" -ForegroundColor Green
Write-Host "????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Green

# Create logs directory
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-LogSection "Configuration"
Write-Log "Project root: $ProjectRoot"
Write-Log "Backend root: $BackendRoot"
Write-Log "Frontend root: $FrontendRoot"
Write-Log "Log file: $LogFile"
Write-Log "Environment: development"

# ==============================================================================
# PREFLIGHT CHECKS
# ==============================================================================

Write-LogSection "Preflight Checks"

# Check config file
if (-not (Test-Path $EnvFile)) {
    Write-Log "??? Development config file not found: $EnvFile"
    Write-Log "  Using defaults from config.py"
} else {
    Write-Log "??? Config file found: $EnvFile"
}

# Check if Docker is available
if (Test-CommandExists "docker") {
    Write-Log "??? Docker is available"
} else {
    Write-Log "??? Docker not found. Please install Docker Desktop for Windows."
    Write-Log "  https://www.docker.com/products/docker-desktop"
    exit 1
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
    Write-Log "??? Port conflicts detected: $($portConflicts -join ', ')"
    Write-Log "  Existing services may still be running."
    Write-Log "  Run '.\stop_photo_organizer.ps1' to clean up."
    exit 1
}
Write-Log "??? No port conflicts detected"

# ==============================================================================
# START DOCKER SERVICES
# ==============================================================================

Write-LogSection "Docker Services"

Write-Log "Starting Docker services..."

# Note: For development, we use a simpler approach than production.
# You may need to customize this for your setup.
Push-Location $DockerDir
try {
    # Start Docker Compose in background
    Write-Log "  ??? Starting PostgreSQL and Redis..."
    $dockerProcess = Start-Process -FilePath "docker-compose" -ArgumentList "up" -NoNewWindow -PassThru

    # Wait for services to be ready
    if (Wait-ForPort -Port $PostgresPort -ServiceName "PostgreSQL" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "??? PostgreSQL is ready"
    } else {
        Write-Log "??? PostgreSQL failed to start"
        Stop-Process -InputObject $dockerProcess -Force
        exit 1
    }

    if (Wait-ForPort -Port $RedisPort -ServiceName "Redis" -TimeoutSeconds 15) {
        Write-Log "??? Redis is ready"
    } else {
        Write-Log "??? Redis failed to start"
        Stop-Process -InputObject $dockerProcess -Force
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

    # Build uvicorn command
    $uvicornArgs = @(
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", $BackendPort
    )
    
    if (-not $NoReload) {
        $uvicornArgs += "--reload"
    }

    # Start backend
    Write-Log "  ??? Command: python -m uvicorn $($uvicornArgs -join ' ')"
    $backendProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn") + $uvicornArgs -NoNewWindow -PassThru

    if (Wait-ForPort -Port $BackendPort -ServiceName "Backend" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "??? Backend is ready"
    } else {
        Write-Log "??? Backend failed to start"
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
    Write-Log "  ??? Command: npm run dev"

    $frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -NoNewWindow -PassThru

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

Write-LogSection "Startup Complete"

$ready = $true
if (-not (Test-PortOpen -Port $PostgresPort)) { $ready = $false }
if (-not (Test-PortOpen -Port $RedisPort)) { $ready = $false }
if (-not (Test-PortOpen -Port $BackendPort)) { $ready = $false }
if (-not (Test-PortOpen -Port $FrontendPort)) { $ready = $false }

if ($ready) {
    Write-Host "??? All services are running" -ForegroundColor Green
    Write-Log "??? All services are running"
    
    Write-Host "`n???? Photo Organizer is ready on http://127.0.0.1:$FrontendPort`n" -ForegroundColor Green
    Write-Log "Browser should open automatically in a few seconds."
    
    # Try to open browser
    try {
        Start-Process "http://127.0.0.1:$FrontendPort"
        Write-Log "??? Browser opened"
    } catch {
        Write-Log "??? Could not open browser automatically. Visit http://127.0.0.1:$FrontendPort manually."
    }
    
    Write-Host "`nTo stop all services, press Ctrl+C or run: .\stop_photo_organizer.ps1`n" -ForegroundColor Cyan
    Write-Log "Operator should use stop script or Ctrl+C to shutdown"
    
    Write-Host "????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????`n" -ForegroundColor Green
    Write-Log "Startup sequence completed successfully"
    
    # Keep script running (Docker runs in background)
    Read-Host "Press Enter to continue (or Ctrl+C to stop)"
} else {
    Write-Host "??? Startup failed. Check log file: $LogFile" -ForegroundColor Red
    Write-Log "??? Startup failed - services not responding"
    exit 1
}

