<#
.SYNOPSIS
Stop Photo Organizer services cleanly.

.DESCRIPTION
Gracefully stops all Photo Organizer services:
- Frontend process
- Backend process
- Docker services (PostgreSQL, Redis)

.EXAMPLE
.\stop_photo_organizer.ps1

.NOTES
This is a v1.0 baseline script.
#>

param(
    [int]$GracefulTimeoutSeconds = 10,
    [int]$FrontendPid = 0,
    [int]$BackendPid = 0
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogsDir = Join-Path (Join-Path (Join-Path $ProjectRoot "storage") "logs") "runtime"
$LogFile = Join-Path $LogsDir "shutdown_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

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

function Test-PortListening {
    param(
        [int]$Port
    )
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Stop-PortListeners {
    param(
        [int]$Port,
        [int]$Retries = 3
    )

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $listeners) {
            return $true
        }

        foreach ($listener in $listeners) {
            $ownerPid = $listener.OwningProcess

            if ($ownerPid -and $ownerPid -gt 0) {
                try {
                    Stop-Process -Id $ownerPid -Force -ErrorAction Stop
                    Write-Log "  -> Stopped listener PID $ownerPid on port $Port"
                } catch {
                    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerPid" -ErrorAction SilentlyContinue
                    if (-not $proc) {
                        Write-Log "  -> Listener PID $ownerPid on port $Port is no longer in process table (ghost listener suspected)"
                    } else {
                        Write-Log "  -> Could not stop PID $ownerPid on port ${Port}: $($_.Exception.Message)"
                    }
                }
            }
        }

        if (Get-Command Remove-NetTCPConnection -ErrorAction SilentlyContinue) {
            try {
                Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                    Remove-NetTCPConnection -ErrorAction Stop
                Write-Log "  -> Requested TCP stack cleanup for port $Port"
            } catch {
                Write-Log "  -> TCP stack cleanup not available for port ${Port}: $($_.Exception.Message)"
            }
        }

        Start-Sleep -Milliseconds 500
    }

    return -not (Test-PortListening -Port $Port)
}

function Stop-ProcessTreeByPid {
    param(
        [int]$TargetPid,
        [string]$Label
    )

    if ($TargetPid -le 0) {
        return $false
    }

    try {
        taskkill /PID $TargetPid /T /F 2>&1 | Out-Null
        Write-Log "  -> Requested process-tree stop for $Label PID $TargetPid"
        return $true
    } catch {
        Write-Log "  -> Could not stop process-tree for $Label PID $TargetPid"
        return $false
    }
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Photo Organizer - Shutdown" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Create logs directory if needed
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-LogSection "Shutdown Sequence"

# Prefer exact launcher PIDs when provided, then fall back to discovery logic.
if ($FrontendPid -gt 0) {
    Stop-ProcessTreeByPid -TargetPid $FrontendPid -Label "frontend" | Out-Null
}
if ($BackendPid -gt 0) {
    Stop-ProcessTreeByPid -TargetPid $BackendPid -Label "backend" | Out-Null
}

# Stop frontend (npm process)
Write-Log "Stopping frontend..."
$frontendStopped = $false
$nodeProcs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "next" }
if ($nodeProcs) {
    foreach ($proc in $nodeProcs) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    $frontendStopped = $true
}

# Fallback: kill any listener on port 3000.
if (Stop-PortListeners -Port 3000 -Retries 2) {
    $frontendStopped = $true
}

if ($frontendStopped) { Write-Log "[OK] Frontend stopped" } else { Write-Log "  (Frontend already stopped)" }

Start-Sleep -Seconds 1

# Stop backend (uvicorn/python process)
Write-Log "Stopping backend..."
$backendStopped = $false
$pythonProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "-m uvicorn" }
if ($pythonProcs) {
    foreach ($proc in $pythonProcs) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    $backendStopped = $true
}

# Fallback: kill any listener on port 8001.
if (Stop-PortListeners -Port 8001 -Retries 4) {
    $backendStopped = $true
}

if ($backendStopped) { Write-Log "[OK] Backend stopped" } else { Write-Log "  (Backend already stopped)" }

Start-Sleep -Seconds 1

# Stop Docker services
Write-Log "Stopping Docker services..."
try {
    $DockerDir = Join-Path $ProjectRoot "docker"
    if (Test-Path $DockerDir) {
        Push-Location $DockerDir
        try {
            # Stop legacy dev project, production project, and prior dev-separation project if present.
            foreach ($proj in @("docker", "photo-organizer-prod", "photo-organizer-dev")) {
                docker compose --project-name $proj down 2>&1 | Out-Null
            }
            Write-Log "[OK] Docker services stopped"
        } catch {
            Write-Log "  (Docker services may already be stopped)"
        } finally {
            Pop-Location
        }
    }
} catch {
    Write-Log "  (Could not stop Docker services: $_)"
}

Write-LogSection "Port Release Verification"
foreach ($port in @(3000, 8001, 5432, 6379)) {
    if (Test-PortListening -Port $port) {
        $released = Stop-PortListeners -Port $port -Retries 3
        if ($released) {
            Write-Log "[OK] Port $port released"
        } else {
            $remaining = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($remaining) {
                Write-Log "[WARN] Port $port still listening (PID $($remaining.OwningProcess))."
            } else {
                Write-Log "[WARN] Port $port still appears busy."
            }
        }
    } else {
        Write-Log "[OK] Port $port is free"
    }
}

Write-LogSection "Shutdown Complete"
Write-Log "[OK] All services stopped"

Write-Host "`n========================================`n" -ForegroundColor Cyan
Write-Log "Shutdown log written to: $LogFile"
Write-Host "Photo Organizer has been stopped.`n" -ForegroundColor Green

