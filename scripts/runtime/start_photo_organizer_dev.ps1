<#
.SYNOPSIS
Start Photo Organizer in development mode.

.DESCRIPTION
Starts the Photo Organizer stack with development configuration:
- Development database (photo_organizer)
- Local storage paths (../storage/*)
- Hot reload enabled
- Development console output

Sets APP_RUNTIME_PROFILE=development before starting the backend.
Uses the legacy Docker Compose project name 'docker' so existing dev data
volume(s) continue to be used.

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

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendRoot = Join-Path $ProjectRoot "backend"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$DockerDir = Join-Path $ProjectRoot "docker"
$LogsDir = Join-Path (Join-Path (Join-Path $ProjectRoot "storage") "logs") "runtime"
$EnvFile = Join-Path $BackendRoot ".env.development"

$LogFile = Join-Path $LogsDir "startup_dev_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Prefer the workspace venv interpreter so runtime dependencies are consistent.
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# Docker Compose project name for legacy dev data continuity.
# Keep this aligned with pre-12.47 behavior (docker_postgres_data).
$DockerProject = "docker"

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
    Write-Log "  [ERROR] $ServiceName did not respond within ${TimeoutSeconds}s"
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
    Write-Log "  [ERROR] $ServiceName did not return HTTP 200 within ${TimeoutSeconds}s"
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
        Write-Log "[ERROR] Docker CLI not found. Please install Docker Desktop for Windows."
        return $false
    }

    if (Wait-ForDockerDaemon -TimeoutSeconds 5) {
        return $true
    }

    Write-Log "[WARN] Docker daemon is not running. Attempting to start Docker Desktop..."
    $dockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopExe) {
        try {
            Start-Process -FilePath $dockerDesktopExe | Out-Null
        } catch {
            Write-Log "[ERROR] Failed to launch Docker Desktop: $_"
            return $false
        }
    } else {
        Write-Log "[ERROR] Docker Desktop executable not found at: $dockerDesktopExe"
        return $false
    }

    Write-Log "  -> Waiting for Docker daemon to become ready..."
    if (-not (Wait-ForDockerDaemon -TimeoutSeconds 90)) {
        Write-Log "[ERROR] Docker daemon did not become ready in time."
        Write-Log "  Open Docker Desktop and wait until it shows 'Engine running', then retry."
        return $false
    }

    Write-Log "[OK] Docker daemon is ready"
    return $true
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Photo Organizer - Development Startup" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Create logs directory
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-LogSection "Configuration"
Write-Log "Project root : $ProjectRoot"
Write-Log "Backend root : $BackendRoot"
Write-Log "Frontend root: $FrontendRoot"
Write-Log "Log file     : $LogFile"
Write-Log "Profile      : development"
Write-Log "Docker project: $DockerProject"
Write-Log "Python exe   : $PythonExe"

# ==============================================================================
# PREFLIGHT CHECKS
# ==============================================================================

Write-LogSection "Preflight Checks"

# Check config file
if (-not (Test-Path $EnvFile)) {
    Write-Log "[WARN] .env.development not found -- using legacy .env fallback or config.py defaults"
} else {
    Write-Log "[OK] Config file found: $EnvFile"
}

# Check if Docker is available
if (Ensure-DockerReady) {
    Write-Log "[OK] Docker is available"
} else {
    Write-Log "[ERROR] Docker is not ready."
    Write-Log "  https://www.docker.com/products/docker-desktop"
    exit 1
}

# Check for port conflicts
$portConflicts = @()
foreach ($port in @($PostgresPort, $RedisPort, $BackendPort, $FrontendPort)) {
    if (Test-PortOpen -Port $port) {
        $portConflicts += $port
    }
}

if ($portConflicts.Count -gt 0) {
    Write-Log "[ERROR] Port conflicts on: $($portConflicts -join ', ')"
    Write-Log "  Run '.\stop_photo_organizer.ps1' to clean up first."
    exit 1
}
Write-Log "[OK] No port conflicts detected"

# ==============================================================================
# START DOCKER SERVICES
# ==============================================================================

Write-LogSection "Docker Services"

# ==============================================================================
# SET RUNTIME PROFILE
# ==============================================================================

Write-LogSection "Runtime Profile"
$env:APP_RUNTIME_PROFILE = "development"
Write-Log "[OK] APP_RUNTIME_PROFILE=development"

# ==============================================================================
# START DOCKER SERVICES
# ==============================================================================

Write-LogSection "Docker Services"

Write-Log "Starting Docker services (project: $DockerProject)..."

Push-Location $DockerDir
try {
    # Use explicit legacy dev project name to preserve existing dev volume binding.
    $dockerProcess = Start-Process -FilePath "docker" -ArgumentList @("compose", "--project-name", $DockerProject, "up", "-d") -NoNewWindow -PassThru -Wait
    if ($dockerProcess.ExitCode -ne 0) {
        Write-Log "[ERROR] Docker compose failed to start services (exit code $($dockerProcess.ExitCode))."
        Write-Log "  Ensure Docker Desktop is open and engine is running, then retry."
        exit 1
    }

    # Wait for services to be ready
    if (Wait-ForPort -Port $PostgresPort -ServiceName "PostgreSQL" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        Write-Log "[OK] PostgreSQL is ready"
    } else {
        Write-Log "[ERROR] PostgreSQL failed to start"
        exit 1
    }

    if (Wait-ForPort -Port $RedisPort -ServiceName "Redis" -TimeoutSeconds 15) {
        Write-Log "[OK] Redis is ready"
    } else {
        Write-Log "[ERROR] Redis failed to start"
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
    Write-Log "  -> Command: $PythonExe -m uvicorn $($uvicornArgs -join ' ')"
    $backendArgList = @("-m", "uvicorn") + $uvicornArgs
    $backendProcess = Start-Process -FilePath $PythonExe -ArgumentList $backendArgList -NoNewWindow -PassThru

    if (Wait-ForPort -Port $BackendPort -ServiceName "Backend" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
        $backendHealthUrl = "http://127.0.0.1:$BackendPort/health"
        if (Wait-ForHttpEndpoint -Url $backendHealthUrl -ServiceName "Backend health" -TimeoutSeconds $ServiceStartTimeoutSeconds) {
            Write-Log "[OK] Backend is ready"
        } else {
            Write-Log "[ERROR] Backend health check failed"
            Stop-Process -InputObject $backendProcess -Force -ErrorAction SilentlyContinue
            exit 1
        }
    } else {
        Write-Log "[ERROR] Backend failed to start"
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
    Write-Log "Starting frontend service (npm run dev)..."

    # On Windows, npm should be launched via npm.cmd when using Start-Process.
    $frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -NoNewWindow -PassThru

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

Write-LogSection "Startup Complete"

$ready = $true
if (-not (Test-PortOpen -Port $PostgresPort)) { $ready = $false; Write-Log "[ERROR] PostgreSQL not responding" }
if (-not (Test-PortOpen -Port $RedisPort))    { $ready = $false; Write-Log "[ERROR] Redis not responding" }
if (-not (Test-PortOpen -Port $BackendPort))  { $ready = $false; Write-Log "[ERROR] Backend not responding" }

if ($ready) {
    Write-Host "`n[OK] Development services are running" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend : http://localhost:$FrontendPort" -ForegroundColor Cyan
    Write-Host "  Backend  : http://localhost:$BackendPort" -ForegroundColor Cyan
    Write-Host "  Health   : http://localhost:$BackendPort/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Log "Startup complete."

    # Try to open browser
    try {
        Start-Process "http://127.0.0.1:$FrontendPort"
        Write-Log "Browser opened"
    } catch {
        Write-Log "Could not open browser automatically. Visit http://127.0.0.1:$FrontendPort manually."
    }

    Write-Host "To stop all services run: .\stop_photo_organizer.ps1`n" -ForegroundColor Cyan
    Write-Log "Startup sequence completed successfully."

    # Keep script running until user requests shutdown, then stop cleanly.
    Read-Host "Press Enter to stop all services and exit"
    Write-Log "Shutdown requested from launcher prompt"
    & (Join-Path $PSScriptRoot "stop_photo_organizer.ps1") -FrontendPid $frontendProcess.Id -BackendPid $backendProcess.Id | Out-Null
    Write-Log "Launcher exit complete"
} else {
    Write-Host "`n[ERROR] Startup failed. Check log: $LogFile" -ForegroundColor Red
    Write-Log "[ERROR] Startup failed -- services not responding"
    exit 1
}

