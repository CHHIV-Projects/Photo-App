<#
.SYNOPSIS
Check Photo Organizer runtime health.

.DESCRIPTION
Performs health checks on Photo Organizer services:
- Docker availability
- PostgreSQL connectivity
- Redis connectivity
- Backend health endpoint
- Frontend availability
- Storage path accessibility

.EXAMPLE
.\check_runtime_health.ps1

.NOTES
This is a v1.0 baseline script. Use for diagnostics and monitoring.
#>

param(
    [int]$TimeoutSeconds = 5
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackendRoot = Join-Path $ProjectRoot "backend"

# Service ports
$PostgresPort = 5432
$RedisPort = 6379
$BackendPort = 8001
$FrontendPort = 3000

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

function Test-PortOpen {
    param($Port, $HostAddress = "127.0.0.1")
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $result = $tcp.BeginConnect($HostAddress, $Port, $null, $null)
        $result.AsyncWaitHandle.WaitOne($TimeoutSeconds * 1000) | Out-Null
        if ($tcp.Connected) {
            $tcp.Close()
            return $true
        }
    } catch { }
    return $false
}

function Test-CommandExists {
    param($Command)
    $result = $null
    try { $result = Get-Command $Command -ErrorAction Stop } catch { }
    return $null -ne $result
}

function Test-HttpEndpoint {
    param($Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Write-HealthResult {
    param($ServiceName, $Status, $Message = "")
    $symbol = if ($Status) { "[OK]" } else { "[ERROR]" }
    $color  = if ($Status) { "Green" } else { "Red" }
    $msg = "$symbol $ServiceName"
    if ($Message) { $msg += ": $Message" }
    Write-Host $msg -ForegroundColor $color
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n========================================" -ForegroundColor Blue
Write-Host "  Photo Organizer - Health Check" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

$allHealthy = $true

# ==============================================================================
# INFRASTRUCTURE HEALTH
# ==============================================================================

Write-Host "Infrastructure`n" -ForegroundColor Cyan

# Docker
if (Test-CommandExists "docker") {
    Write-HealthResult "Docker" $true
} else {
    Write-HealthResult "Docker" $false "Not installed or not in PATH"
    $allHealthy = $false
}

# ==============================================================================
# SERVICES HEALTH
# ==============================================================================

Write-Host "`nServices`n" -ForegroundColor Cyan

# PostgreSQL
$postgresUp = Test-PortOpen -Port $PostgresPort
Write-HealthResult "PostgreSQL" $postgresUp "localhost:$PostgresPort"
if (-not $postgresUp) { $allHealthy = $false }

# Redis
$redisUp = Test-PortOpen -Port $RedisPort
Write-HealthResult "Redis" $redisUp "localhost:$RedisPort"
if (-not $redisUp) { $allHealthy = $false }

# Check backend + show /health JSON if available
$backendUp = Test-PortOpen -Port $BackendPort
if ($backendUp) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-HealthResult "Backend" $true "localhost:$BackendPort (/health)"
            Write-Host "  Health response: $($response.Content)" -ForegroundColor DarkGray
        } else {
            Write-HealthResult "Backend" $false "localhost:$BackendPort (/health returned $($response.StatusCode))"
            $allHealthy = $false
        }
    } catch {
        Write-HealthResult "Backend" $false "localhost:$BackendPort (port open but /health failed)"
        $allHealthy = $false
    }
} else {
    Write-HealthResult "Backend" $false "localhost:$BackendPort (not responding)"
    $allHealthy = $false
}

# Frontend
$frontendUp = Test-PortOpen -Port $FrontendPort
Write-HealthResult "Frontend" $frontendUp "localhost:$FrontendPort"
if (-not $frontendUp) { $allHealthy = $false }

# ==============================================================================
# STORAGE HEALTH
# ==============================================================================

Write-Host "`nStorage`n" -ForegroundColor Cyan

# Check standard storage paths
$storageDir = Join-Path $ProjectRoot "storage"
if (Test-Path $storageDir) {
    Write-HealthResult "Storage directory" $true $storageDir
} else {
    Write-HealthResult "Storage directory" $false "Not found at $storageDir"
    $allHealthy = $false
}

$vaultDir = Join-Path $storageDir "vault"
if (Test-Path $vaultDir) {
    Write-HealthResult "Vault directory" $true
} else {
    Write-HealthResult "Vault directory" $false "Not found at $vaultDir"
    # Not fatal for health check, might be on NAS
}

$logsDir = Join-Path $storageDir "logs"
if (Test-Path $logsDir) {
    Write-HealthResult "Logs directory" $true
} else {
    Write-HealthResult "Logs directory" $false "Not found at $logsDir"
}

# ==============================================================================
# SUMMARY
# ==============================================================================

Write-Host "`n========================================`n"

if ($allHealthy) {
    Write-Host "`n[OK] All critical services are healthy`n" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[ERROR] Some services are not healthy. Please check above.`n" -ForegroundColor Red
    Write-Host "  Start services with: .\start_photo_organizer_dev.ps1`n" -ForegroundColor Yellow
    exit 1
}

