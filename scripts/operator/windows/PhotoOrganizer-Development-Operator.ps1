[CmdletBinding()]
param(
    [switch]$SelfTest,
    [switch]$LaunchDetached,
    [ValidateSet("None", "Start", "Stop", "Status")]
    [string]$TunnelWorkerAction = "None",
    [string]$TunnelOperationId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($LaunchDetached) {
    $controllerLiteral = "'" + $PSCommandPath.Replace("'", "''") + "'"
    $childCommand = "& $controllerLiteral"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($childCommand))
    $windowsPowerShell = Join-Path $PSHOME "powershell.exe"
    Start-Process `
        -FilePath $windowsPowerShell `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-WindowStyle", "Hidden", "-EncodedCommand", $encodedCommand) `
        -WindowStyle Hidden | Out-Null
    exit 0
}

$script:ControllerId = "PhotoOrganizerDevelopmentOperator"
$script:ControllerVersion = "1.0.0"
$script:SshHost = "henderson-server1"
$script:RemoteRepository = "/home/chuck/projects/photo-organizer-dev"
$script:RemoteOperatorScript = "/home/chuck/projects/photo-organizer-dev/scripts/operator/development/photo_organizer_dev_operator.sh"
$script:FrontendUrl = "http://localhost:13000"
$script:BackendHealthUrl = "http://localhost:18001/health"
$script:VsCodeFolderUri = "vscode-remote://ssh-remote+henderson-server1/home/chuck/projects/photo-organizer-dev"
$script:WinScpSession = "henderson-server1"
$script:ApprovedInstallPath = "C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator"
$script:StateDirectory = if ($env:LOCALAPPDATA) {
    Join-Path $env:LOCALAPPDATA "PhotoOrganizer\DevelopmentOperator"
} else {
    $null
}
$script:StatePath = if ($script:StateDirectory) {
    Join-Path $script:StateDirectory "tunnel-state.json"
} else {
    $null
}
$script:ForwardFrontend = "127.0.0.1:13000:127.0.0.1:13000"
$script:ForwardBackend = "127.0.0.1:18001:127.0.0.1:18001"
$script:AllowedRemoteActions = @{
    "start" = "Start Development Stack"
    "stop" = "Stop Development Stack"
    "status" = "Show Stack Status"
    "logs" = "Show Recent Logs"
    "follow-logs" = "Follow Live Logs"
}
$script:LastAction = "Controller opened"
$script:LastMessage = "Checking tunnel and server status in the background."
$script:LastSeverity = "WARNING"
$script:CachedServerStatus = "CHECKING"
$script:CachedTunnelStatus = "CHECKING"
$script:CachedTunnelActive = $false
$script:CachedTunnelPid = $null
$script:CachedPort13000Available = $null
$script:CachedPort18001Available = $null
$script:TunnelOperation = $null
$script:TunnelCompletionInProgress = $false
$script:ControllerForm = $null

function Get-ApplicationPath {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandNames,
        [string[]]$FallbackPaths = @()
    )

    foreach ($commandName in $CommandNames) {
        $command = Get-Command -Name $commandName -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($command -and $command.Source) {
            return [System.IO.Path]::GetFullPath($command.Source)
        }
    }

    foreach ($candidate in $FallbackPaths) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return [System.IO.Path]::GetFullPath($candidate)
        }
    }

    return $null
}

function Get-SshExecutable {
    $fallbacks = @()
    if ($env:WINDIR) {
        $fallbacks += (Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe")
    }
    return Get-ApplicationPath -CommandNames @("ssh.exe", "ssh") -FallbackPaths $fallbacks
}

function Get-WindowsPowerShellExecutable {
    $fallbacks = @()
    if ($PSHOME) {
        $fallbacks += (Join-Path $PSHOME "powershell.exe")
    }
    if ($env:WINDIR) {
        $fallbacks += (Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe")
    }
    return Get-ApplicationPath -CommandNames @("powershell.exe", "powershell") -FallbackPaths $fallbacks
}

function Get-VsCodeExecutable {
    $fallbacks = @()
    if ($env:LOCALAPPDATA) {
        $fallbacks += (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\Code.exe")
        $fallbacks += (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\bin\code.cmd")
    }
    if ($env:ProgramFiles) {
        $fallbacks += (Join-Path $env:ProgramFiles "Microsoft VS Code\Code.exe")
        $fallbacks += (Join-Path $env:ProgramFiles "Microsoft VS Code\bin\code.cmd")
    }
    return Get-ApplicationPath -CommandNames @("code.cmd", "code.exe", "code") -FallbackPaths $fallbacks
}

function Get-WinScpExecutable {
    $fallbacks = @()
    if ($env:ProgramFiles) {
        $fallbacks += (Join-Path $env:ProgramFiles "WinSCP\WinSCP.exe")
    }
    $programFilesX86 = ${env:ProgramFiles(x86)}
    if ($programFilesX86) {
        $fallbacks += (Join-Path $programFilesX86 "WinSCP\WinSCP.exe")
    }
    if ($env:LOCALAPPDATA) {
        $fallbacks += (Join-Path $env:LOCALAPPDATA "Programs\WinSCP\WinSCP.exe")
    }
    return Get-ApplicationPath -CommandNames @("WinSCP.exe") -FallbackPaths $fallbacks
}

$script:SshExecutable = Get-SshExecutable
$script:PowerShellExecutable = Get-WindowsPowerShellExecutable
$script:VsCodeExecutable = Get-VsCodeExecutable
$script:WinScpExecutable = Get-WinScpExecutable

function Invoke-WithTunnelMutex {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Operation
    )

    $mutex = New-Object System.Threading.Mutex($false, "Local\PhotoOrganizerDevelopmentOperatorTunnel")
    $acquired = $false
    try {
        try {
            $acquired = $mutex.WaitOne(10000)
        } catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
        }
        if (-not $acquired) {
            throw "Another Photo Organizer controller is changing tunnel state. Try again in a moment."
        }
        return & $Operation
    } finally {
        if ($acquired) {
            $mutex.ReleaseMutex()
        }
        $mutex.Dispose()
    }
}

function Get-TunnelArguments {
    return @(
        "-N",
        "-T",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=60",
        "-o", "ServerAliveCountMax=3",
        "-L", $script:ForwardFrontend,
        "-L", $script:ForwardBackend,
        $script:SshHost
    )
}

function Test-LocalPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener -ArgumentList ([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

function Test-LocalPortListening {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutMilliseconds = 500
    )

    $client = New-Object System.Net.Sockets.TcpClient
    $asyncResult = $null
    try {
        $asyncResult = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)) {
            return $false
        }
        $client.EndConnect($asyncResult)
        return $client.Connected
    } catch {
        return $false
    } finally {
        if ($asyncResult -and $asyncResult.AsyncWaitHandle) {
            $asyncResult.AsyncWaitHandle.Close()
        }
        $client.Close()
    }
}

function Read-TunnelState {
    if (-not $script:StatePath -or -not (Test-Path -LiteralPath $script:StatePath -PathType Leaf)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $script:StatePath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return [pscustomobject]@{
            StateReadError = $_.Exception.Message
        }
    }
}

function Remove-TunnelState {
    if ($script:StatePath -and (Test-Path -LiteralPath $script:StatePath -PathType Leaf)) {
        Remove-Item -LiteralPath $script:StatePath -Force -ErrorAction Stop
    }
}

function Initialize-TunnelStateStorage {
    if (-not $script:StateDirectory -or -not $script:StatePath) {
        throw "LOCALAPPDATA is unavailable; managed tunnel state cannot be stored safely."
    }

    if (-not (Test-Path -LiteralPath $script:StateDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $script:StateDirectory -Force | Out-Null
    }

    $writeProbe = Join-Path $script:StateDirectory (".write-probe-{0}.tmp" -f [System.Diagnostics.Process]::GetCurrentProcess().Id)
    try {
        [System.IO.File]::WriteAllText($writeProbe, "Photo Organizer operator state write test")
    } finally {
        if (Test-Path -LiteralPath $writeProbe -PathType Leaf) {
            Remove-Item -LiteralPath $writeProbe -Force -ErrorAction SilentlyContinue
        }
    }
}

function Write-TunnelState {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    if (-not $script:StateDirectory -or -not $script:StatePath) {
        throw "LOCALAPPDATA is unavailable; managed tunnel state cannot be stored safely."
    }

    if (-not (Test-Path -LiteralPath $script:StateDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $script:StateDirectory -Force | Out-Null
    }

    $Process.Refresh()
    $state = [ordered]@{
        ControllerId = $script:ControllerId
        ControllerVersion = $script:ControllerVersion
        Pid = $Process.Id
        StartTimeUtc = $Process.StartTime.ToUniversalTime().ToString("o")
        ExecutablePath = $script:SshExecutable
        Host = $script:SshHost
        Forwards = @($script:ForwardFrontend, $script:ForwardBackend)
    }

    $temporaryStatePath = "$($script:StatePath).$([System.Diagnostics.Process]::GetCurrentProcess().Id).tmp"
    try {
        $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporaryStatePath -Encoding UTF8
        Move-Item -LiteralPath $temporaryStatePath -Destination $script:StatePath -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryStatePath -PathType Leaf) {
            Remove-Item -LiteralPath $temporaryStatePath -Force -ErrorAction SilentlyContinue
        }
    }
}

function New-TunnelValidationResult {
    param(
        [bool]$IsValid,
        [bool]$IsStale,
        [string]$Reason,
        $State = $null,
        $Process = $null
    )

    return [pscustomobject]@{
        IsValid = $IsValid
        IsStale = $IsStale
        Reason = $Reason
        State = $State
        Process = $Process
    }
}

function Test-ManagedTunnelCommandLine {
    param([Parameter(Mandatory = $true)][string]$CommandLine)

    foreach ($marker in @(
        "BatchMode=yes",
        "ExitOnForwardFailure=yes",
        "ServerAliveInterval=60",
        "ServerAliveCountMax=3",
        $script:SshHost,
        $script:ForwardFrontend,
        $script:ForwardBackend
    )) {
        if ($CommandLine.IndexOf($marker, [StringComparison]::Ordinal) -lt 0) {
            return $false
        }
    }

    if (-not [regex]::IsMatch($CommandLine, '(?i)(^|\s)-N(\s|$)') -or
        -not [regex]::IsMatch($CommandLine, '(?i)(^|\s)-T(\s|$)')) {
        return $false
    }
    if ([regex]::Matches($CommandLine, '(?i)(^|\s)-L(\s|$)').Count -ne 2) {
        return $false
    }
    if ([regex]::IsMatch($CommandLine, '(?i)(^|\s)-(R|D)(\s|$)')) {
        return $false
    }

    return $true
}

function Test-ManagedTunnel {
    $state = Read-TunnelState
    if (-not $state) {
        return New-TunnelValidationResult -IsValid $false -IsStale $false -Reason "No managed tunnel state exists."
    }

    if ($state.PSObject.Properties.Name -contains "StateReadError") {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "Tunnel state is unreadable JSON." -State $state
    }

    $requiredProperties = @(
        "ControllerId", "ControllerVersion", "Pid", "StartTimeUtc",
        "ExecutablePath", "Host", "Forwards"
    )
    foreach ($propertyName in $requiredProperties) {
        if (-not ($state.PSObject.Properties.Name -contains $propertyName)) {
            return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "Tunnel state is missing $propertyName." -State $state
        }
    }

    if ($state.ControllerId -ne $script:ControllerId -or $state.Host -ne $script:SshHost) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "Tunnel state does not identify this controller and host." -State $state
    }

    $stateForwards = @($state.Forwards)
    if ($stateForwards.Count -ne 2 -or
        -not ($stateForwards -contains $script:ForwardFrontend) -or
        -not ($stateForwards -contains $script:ForwardBackend)) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "Tunnel state does not contain the exact approved forwards." -State $state
    }

    $targetProcessId = 0
    if (-not [int]::TryParse([string]$state.Pid, [ref]$targetProcessId) -or $targetProcessId -le 0) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "Tunnel state contains an invalid process ID." -State $state
    }

    $process = Get-Process -Id $targetProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "The recorded tunnel process no longer exists." -State $state
    }

    try {
        $recordedStart = [DateTime]::Parse(
            [string]$state.StartTimeUtc,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind
        ).ToUniversalTime()
        $actualStart = $process.StartTime.ToUniversalTime()
    } catch {
        return New-TunnelValidationResult -IsValid $false -IsStale $false -Reason "The process start time cannot be verified safely." -State $state -Process $process
    }

    if ($recordedStart.Ticks -ne $actualStart.Ticks) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "The recorded PID has been reused by another process." -State $state -Process $process
    }

    $cimProcess = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $targetProcessId" -ErrorAction SilentlyContinue
    if (-not $cimProcess -or -not $cimProcess.ExecutablePath -or -not $cimProcess.CommandLine) {
        return New-TunnelValidationResult -IsValid $false -IsStale $false -Reason "Windows did not expose enough process identity to verify the tunnel." -State $state -Process $process
    }

    try {
        $recordedExecutable = [System.IO.Path]::GetFullPath([string]$state.ExecutablePath)
        $actualExecutable = [System.IO.Path]::GetFullPath([string]$cimProcess.ExecutablePath)
        $expectedExecutable = [System.IO.Path]::GetFullPath([string]$script:SshExecutable)
    } catch {
        return New-TunnelValidationResult -IsValid $false -IsStale $false -Reason "The SSH executable path cannot be normalized safely." -State $state -Process $process
    }

    if (-not [StringComparer]::OrdinalIgnoreCase.Equals($recordedExecutable, $actualExecutable) -or
        -not [StringComparer]::OrdinalIgnoreCase.Equals($expectedExecutable, $actualExecutable) -or
        [System.IO.Path]::GetFileName($actualExecutable) -ine "ssh.exe") {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "The recorded PID is not the expected Windows SSH executable." -State $state -Process $process
    }

    $commandLine = [string]$cimProcess.CommandLine
    if (-not (Test-ManagedTunnelCommandLine -CommandLine $commandLine)) {
        return New-TunnelValidationResult -IsValid $false -IsStale $true -Reason "The recorded process command line is not the exact managed tunnel." -State $state -Process $process
    }

    return New-TunnelValidationResult -IsValid $true -IsStale $false -Reason "Managed tunnel identity is valid." -State $state -Process $process
}

function Clear-ConfirmedStaleState {
    param($Validation)

    if ($Validation -and -not $Validation.IsValid -and $Validation.IsStale) {
        Remove-TunnelState
        return $true
    }
    return $false
}

function Wait-ForManagedForwards {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds = 15
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $Process.Refresh()
        if ($Process.HasExited) {
            return $false
        }
        if ((Test-LocalPortListening -Port 13000) -and (Test-LocalPortListening -Port 18001)) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}

function Test-DirectManagedTunnelProcess {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    try {
        $Process.Refresh()
        if ($Process.HasExited) {
            return $false
        }

        $currentProcess = Get-Process -Id $Process.Id -ErrorAction Stop
        if ($currentProcess.StartTime.ToUniversalTime().Ticks -ne $Process.StartTime.ToUniversalTime().Ticks) {
            return $false
        }

        $cimProcess = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($Process.Id)" -ErrorAction Stop
        if (-not $cimProcess.ExecutablePath -or -not $cimProcess.CommandLine) {
            return $false
        }

        $actualExecutable = [System.IO.Path]::GetFullPath([string]$cimProcess.ExecutablePath)
        $expectedExecutable = [System.IO.Path]::GetFullPath([string]$script:SshExecutable)
        if (-not [StringComparer]::OrdinalIgnoreCase.Equals($actualExecutable, $expectedExecutable) -or
            [System.IO.Path]::GetFileName($actualExecutable) -ine "ssh.exe") {
            return $false
        }

        $commandLine = [string]$cimProcess.CommandLine
        return Test-ManagedTunnelCommandLine -CommandLine $commandLine
    } catch {
        return $false
    }
}

function Start-ManagedTunnel {
    if (-not $script:SshExecutable) {
        throw "Windows OpenSSH was not found."
    }

    $validation = Test-ManagedTunnel
    if ($validation.IsValid) {
        return [pscustomobject]@{
            Success = $true
            Reused = $true
            Message = "The managed tunnel is already active."
            TunnelActive = $true
            TunnelStatus = "ACTIVE - verified managed SSH tunnel (PID $($validation.Process.Id))"
            TunnelPid = $validation.Process.Id
            Port13000Available = $false
            Port18001Available = $false
        }
    }

    if ($validation.IsStale) {
        Clear-ConfirmedStaleState -Validation $validation | Out-Null
    } elseif ($validation.State) {
        throw "Existing tunnel state cannot be verified safely: $($validation.Reason)"
    }

    Initialize-TunnelStateStorage

    $blockedPorts = @()
    foreach ($port in @(13000, 18001)) {
        if (-not (Test-LocalPortAvailable -Port $port)) {
            $blockedPorts += $port
        }
    }
    if ($blockedPorts.Count -gt 0) {
        throw "Local port conflict on $($blockedPorts -join ', '). No process was terminated."
    }

    $arguments = Get-TunnelArguments
    $process = Start-Process `
        -FilePath $script:SshExecutable `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -PassThru

    try {
        Write-TunnelState -Process $process
        if (-not (Wait-ForManagedForwards -Process $process -TimeoutSeconds 15)) {
            throw "SSH forwarding did not become available."
        }
    } catch {
        $startFailure = $_
        $process.Refresh()
        $identityProven = Test-DirectManagedTunnelProcess -Process $process
        if (-not $process.HasExited -and $identityProven) {
            $process.Kill()
            $process.WaitForExit(5000) | Out-Null
            $process.Refresh()
        }

        if ($process.HasExited -or $identityProven) {
            Remove-TunnelState
        } else {
            $failedValidation = Test-ManagedTunnel
            if ($failedValidation.IsStale) {
                Clear-ConfirmedStaleState -Validation $failedValidation | Out-Null
            }
        }

        throw "$($startFailure.Exception.Message) No unrelated process was terminated."
    }

    return [pscustomobject]@{
        Success = $true
        Reused = $false
        Message = "Managed tunnel started on localhost ports 13000 and 18001."
        TunnelActive = $true
        TunnelStatus = "ACTIVE - managed SSH tunnel started (PID $($process.Id))"
        TunnelPid = $process.Id
        Port13000Available = $false
        Port18001Available = $false
    }
}

function New-InactiveTunnelActionResult {
    param([Parameter(Mandatory = $true)][string]$Message)

    return [pscustomobject]@{
        Success = $true
        Message = $Message
        TunnelActive = $false
        TunnelStatus = "INACTIVE"
        TunnelPid = $null
        Port13000Available = Test-LocalPortAvailable -Port 13000
        Port18001Available = Test-LocalPortAvailable -Port 18001
    }
}

function Stop-ManagedTunnel {
    $validation = Test-ManagedTunnel
    if (-not $validation.IsValid) {
        if ($validation.IsStale) {
            Clear-ConfirmedStaleState -Validation $validation | Out-Null
            return New-InactiveTunnelActionResult -Message "Stale tunnel state was removed. No process was terminated."
        }
        if (-not $validation.State) {
            return New-InactiveTunnelActionResult -Message "No managed tunnel is active."
        }
        throw "Tunnel process identity cannot be proven; nothing was terminated. $($validation.Reason)"
    }

    $validation.Process.Kill()
    $validation.Process.WaitForExit(10000) | Out-Null
    $validation.Process.Refresh()
    if (-not $validation.Process.HasExited) {
        throw "The verified managed tunnel did not stop within 10 seconds."
    }

    Remove-TunnelState

    $result = New-InactiveTunnelActionResult -Message "Managed tunnel stopped."
    $occupiedAfterStop = @()
    if (-not $result.Port13000Available) { $occupiedAfterStop += 13000 }
    if (-not $result.Port18001Available) { $occupiedAfterStop += 18001 }
    if ($occupiedAfterStop.Count -gt 0) {
        $result.Message = "Managed tunnel stopped. Port $($occupiedAfterStop -join ', ') is now occupied by another process; it was left untouched."
        return $result
    }

    $result.Message = "Managed tunnel stopped and both local ports are free."
    return $result
}

function Test-ServerConnection {
    if (-not $script:SshExecutable) {
        return [pscustomobject]@{ Success = $false; Message = "Windows OpenSSH is unavailable." }
    }

    $output = & $script:SshExecutable `
        -o "BatchMode=yes" `
        -o "ConnectTimeout=5" `
        $script:SshHost `
        -- true 2>&1
    if ($LASTEXITCODE -eq 0) {
        return [pscustomobject]@{ Success = $true; Message = "Server connection available." }
    }

    return [pscustomobject]@{
        Success = $false
        Message = "Server connection unavailable. Check network and the henderson-server1 SSH alias."
    }
}

function Invoke-RemoteHealthCheck {
    if (-not $script:SshExecutable) {
        return [pscustomobject]@{ Success = $false; Message = "Windows OpenSSH is unavailable." }
    }

    $output = & $script:SshExecutable `
        -o "BatchMode=yes" `
        -o "ConnectTimeout=8" `
        $script:SshHost `
        -- bash $script:RemoteOperatorScript health 2>&1
    $text = ($output | Out-String).Trim()
    if ($LASTEXITCODE -eq 0) {
        return [pscustomobject]@{
            Success = $true
            Message = if ($text) { $text } else { "Application health checks passed." }
        }
    }

    return [pscustomobject]@{
        Success = $false
        Message = if ($text) { $text } else { "Application health checks failed." }
    }
}

function Get-TunnelOperationResultPath {
    param([Parameter(Mandatory = $true)][Guid]$OperationId)
    if (-not $script:StateDirectory) {
        throw "LOCALAPPDATA is unavailable; tunnel operation state cannot be stored safely."
    }
    return Join-Path $script:StateDirectory ("tunnel-operation-{0}.json" -f $OperationId.ToString("N"))
}

function Get-TunnelSnapshot {
    param([switch]$IncludeServerConnection)

    $validation = Test-ManagedTunnel
    if ($validation.IsStale) {
        Clear-ConfirmedStaleState -Validation $validation | Out-Null
        $validation = Test-ManagedTunnel
    }

    $server = if ($IncludeServerConnection) {
        Test-ServerConnection
    } else {
        $null
    }
    $tunnelStatus = if ($validation.IsValid) {
        "ACTIVE - verified managed SSH tunnel (PID $($validation.Process.Id))"
    } elseif ($validation.State) {
        "WARNING - state exists but process identity cannot be proven"
    } else {
        "INACTIVE"
    }

    return [ordered]@{
        TunnelSnapshotIncluded = $true
        TunnelActive = [bool]$validation.IsValid
        TunnelStatus = $tunnelStatus
        TunnelPid = if ($validation.IsValid) { $validation.Process.Id } else { $null }
        Port13000Available = Test-LocalPortAvailable -Port 13000
        Port18001Available = Test-LocalPortAvailable -Port 18001
        ServerStatusIncluded = [bool]$IncludeServerConnection
        ServerAvailable = if ($server) { [bool]$server.Success } else { $null }
        ServerMessage = if ($server) { [string]$server.Message } else { "" }
    }
}

function Write-TunnelWorkerResult {
    param(
        [Parameter(Mandatory = $true)][Guid]$OperationId,
        [Parameter(Mandatory = $true)]$Result
    )

    if (-not (Test-Path -LiteralPath $script:StateDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $script:StateDirectory -Force | Out-Null
    }
    $resultPath = Get-TunnelOperationResultPath -OperationId $OperationId
    $temporaryResultPath = "$resultPath.tmp"
    try {
        $Result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temporaryResultPath -Encoding UTF8
        Move-Item -LiteralPath $temporaryResultPath -Destination $resultPath -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryResultPath -PathType Leaf) {
            Remove-Item -LiteralPath $temporaryResultPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-TunnelWorkerMode {
    $operationId = [Guid]::Empty
    if (-not [Guid]::TryParse($TunnelOperationId, [ref]$operationId) -or $operationId -eq [Guid]::Empty) {
        Write-Error "A valid controller-generated tunnel operation ID is required."
        return 2
    }

    $actionMessage = "Tunnel status refreshed."
    $actionSucceeded = $true
    $actionResult = $null
    $snapshot = $null
    try {
        switch ($TunnelWorkerAction) {
            "Start" {
                $actionResult = Invoke-WithTunnelMutex -Operation { Start-ManagedTunnel }
                $actionMessage = [string]$actionResult.Message
            }
            "Stop" {
                $actionResult = Invoke-WithTunnelMutex -Operation { Stop-ManagedTunnel }
                $actionMessage = [string]$actionResult.Message
            }
            "Status" {
                $null = Invoke-WithTunnelMutex -Operation { $true }
                $snapshot = Get-TunnelSnapshot -IncludeServerConnection
            }
            default {
                throw "Tunnel worker action is not allowlisted."
            }
        }
    } catch {
        $actionSucceeded = $false
        $actionMessage = $_.Exception.Message
    }

    if ($actionSucceeded -and $null -ne $actionResult) {
        $snapshot = [ordered]@{
            TunnelSnapshotIncluded = $true
            TunnelActive = [bool]$actionResult.TunnelActive
            TunnelStatus = [string]$actionResult.TunnelStatus
            TunnelPid = $actionResult.TunnelPid
            Port13000Available = $actionResult.Port13000Available
            Port18001Available = $actionResult.Port18001Available
            ServerStatusIncluded = $false
            ServerAvailable = $null
            ServerMessage = ""
        }
    } elseif ($null -eq $snapshot) {
        $isStatusAction = $TunnelWorkerAction -eq "Status"
        $snapshot = [ordered]@{
            TunnelSnapshotIncluded = $isStatusAction
            TunnelActive = $false
            TunnelStatus = "UNKNOWN - background validation failed"
            TunnelPid = $null
            Port13000Available = $null
            Port18001Available = $null
            ServerStatusIncluded = $isStatusAction
            ServerAvailable = $false
            ServerMessage = $actionMessage
        }
    }

    $result = [ordered]@{
        Action = $TunnelWorkerAction
        Success = $actionSucceeded
        Message = $actionMessage
        TunnelSnapshotIncluded = $snapshot.TunnelSnapshotIncluded
        TunnelActive = $snapshot.TunnelActive
        TunnelStatus = $snapshot.TunnelStatus
        TunnelPid = $snapshot.TunnelPid
        Port13000Available = $snapshot.Port13000Available
        Port18001Available = $snapshot.Port18001Available
        ServerStatusIncluded = $snapshot.ServerStatusIncluded
        ServerAvailable = $snapshot.ServerAvailable
        ServerMessage = $snapshot.ServerMessage
    }
    Write-TunnelWorkerResult -OperationId $operationId -Result $result
    return $(if ($actionSucceeded) { 0 } else { 1 })
}

function ConvertTo-EncodedPowerShellCommand {
    param([Parameter(Mandatory = $true)][string]$Command)
    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
}

function Quote-PowerShellLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-RemoteActionTerminalCommand {
    param([Parameter(Mandatory = $true)][string]$Action)

    $sshCommandPath = if ($script:SshExecutable) { $script:SshExecutable } else { "ssh.exe" }
    $sshLiteral = Quote-PowerShellLiteral $sshCommandPath
    $hostLiteral = Quote-PowerShellLiteral $script:SshHost
    $scriptLiteral = Quote-PowerShellLiteral $script:RemoteOperatorScript
    $actionLiteral = Quote-PowerShellLiteral $Action
    $titleLiteral = Quote-PowerShellLiteral ("Photo Organizer - " + $script:AllowedRemoteActions[$Action])

    if ($Action -eq "follow-logs") {
        return @"
`$Host.UI.RawUI.WindowTitle = $titleLiteral
& $sshLiteral -t $hostLiteral -- bash $scriptLiteral $actionLiteral
`$remoteExitCode = `$LASTEXITCODE
if (`$remoteExitCode -eq 130) {
    Write-Host "`nLive log following stopped by user." -ForegroundColor Cyan
    `$remoteExitCode = 0
} elseif (`$remoteExitCode -eq 0) {
    Write-Host "`nAction completed successfully." -ForegroundColor Green
} else {
    Write-Host "`nAction failed with exit code `$remoteExitCode." -ForegroundColor Red
}
Read-Host "Press Enter to close this window"
exit `$remoteExitCode
"@
    }

    return @"
`$Host.UI.RawUI.WindowTitle = $titleLiteral
& $sshLiteral -t $hostLiteral -- bash $scriptLiteral $actionLiteral
`$remoteExitCode = `$LASTEXITCODE
if (`$remoteExitCode -eq 0) {
    Write-Host "`nAction completed successfully." -ForegroundColor Green
} else {
    Write-Host "`nAction failed with exit code `$remoteExitCode." -ForegroundColor Red
}
Read-Host "Press Enter to close this window"
exit `$remoteExitCode
"@
}

function Start-VisibleRemoteAction {
    param([Parameter(Mandatory = $true)][string]$Action)

    if (-not $script:AllowedRemoteActions.ContainsKey($Action)) {
        throw "Remote action is not allowlisted."
    }
    if (-not $script:SshExecutable) {
        throw "Windows OpenSSH was not found."
    }
    if (-not $script:PowerShellExecutable) {
        throw "Windows PowerShell was not found."
    }

    $terminalCommand = Get-RemoteActionTerminalCommand -Action $Action
    $encodedCommand = ConvertTo-EncodedPowerShellCommand -Command $terminalCommand
    Start-Process `
        -FilePath $script:PowerShellExecutable `
        -ArgumentList @("-NoProfile", "-EncodedCommand", $encodedCommand) | Out-Null
}

function Get-TunnelWorkerInvocationCommand {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Start", "Stop", "Status")]
        [string]$Action,
        [Parameter(Mandatory = $true)][Guid]$OperationId
    )

    $controllerLiteral = Quote-PowerShellLiteral $PSCommandPath
    $actionLiteral = Quote-PowerShellLiteral $Action
    $operationIdLiteral = Quote-PowerShellLiteral $OperationId.ToString("D")
    return "& $controllerLiteral -TunnelWorkerAction $actionLiteral -TunnelOperationId $operationIdLiteral"
}

function Open-RemoteVsCode {
    if (-not $script:VsCodeExecutable) {
        throw "VS Code CLI was not found. Open VS Code, connect to henderson-server1, and open $($script:RemoteRepository)."
    }

    Start-Process `
        -FilePath $script:VsCodeExecutable `
        -ArgumentList @("--folder-uri", $script:VsCodeFolderUri) | Out-Null
}

function Open-WinScpSession {
    if (-not $script:WinScpExecutable) {
        throw "WinSCP was not found. Open WinSCP normally and select the saved henderson-server1 session."
    }

    Start-Process `
        -FilePath $script:WinScpExecutable `
        -ArgumentList @($script:WinScpSession) | Out-Null
}

function Invoke-ControllerSelfTest {
    $failures = New-Object System.Collections.Generic.List[string]

    function Record-SelfTest {
        param([string]$Label, [bool]$Passed, [string]$Detail)
        $prefix = if ($Passed) { "PASS" } else { "FAIL" }
        Write-Host "$prefix`: $Label - $Detail"
        if (-not $Passed) {
            $failures.Add("$Label`: $Detail")
        }
    }

    Record-SelfTest "SSH host" ($script:SshHost -eq "henderson-server1") $script:SshHost
    Record-SelfTest "remote repository" ($script:RemoteRepository -eq "/home/chuck/projects/photo-organizer-dev") $script:RemoteRepository
    Record-SelfTest "remote operator" ($script:RemoteOperatorScript -eq "/home/chuck/projects/photo-organizer-dev/scripts/operator/development/photo_organizer_dev_operator.sh") $script:RemoteOperatorScript
    Record-SelfTest "installation path" ($script:ApprovedInstallPath -eq "C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator") $script:ApprovedInstallPath
    Record-SelfTest "state path" ($script:StatePath -eq (Join-Path $env:LOCALAPPDATA "PhotoOrganizer\DevelopmentOperator\tunnel-state.json")) $script:StatePath
    Record-SelfTest "state outside OneDrive" (-not $script:StatePath.StartsWith($script:ApprovedInstallPath, [StringComparison]::OrdinalIgnoreCase)) $script:StatePath
    Record-SelfTest "SSH executable" ([bool]$script:SshExecutable) $(if ($script:SshExecutable) { $script:SshExecutable } else { "not found" })
    Record-SelfTest "Windows PowerShell" ([bool]$script:PowerShellExecutable) $(if ($script:PowerShellExecutable) { $script:PowerShellExecutable } else { "not found" })
    Record-SelfTest "VS Code" ([bool]$script:VsCodeExecutable) $(if ($script:VsCodeExecutable) { $script:VsCodeExecutable } else { "not found" })
    Record-SelfTest "WinSCP" ([bool]$script:WinScpExecutable) $(if ($script:WinScpExecutable) { $script:WinScpExecutable } else { "not found" })

    $launcherPath = Join-Path $PSScriptRoot "PhotoOrganizer-Development-Operator.cmd"
    Record-SelfTest "launcher beside controller" (Test-Path -LiteralPath $launcherPath -PathType Leaf) $launcherPath
    if (Test-Path -LiteralPath $launcherPath -PathType Leaf) {
        $launcherText = Get-Content -LiteralPath $launcherPath -Raw
        Record-SelfTest `
            "detached hidden launcher" `
            ($launcherText.Contains("-STA -WindowStyle Hidden -File") -and
                $launcherText.Contains("-LaunchDetached")) `
            "hidden bootstrap launches the detached controller"
    }

    $expectedTunnelArguments = @(
        "-N", "-T", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=60", "-o", "ServerAliveCountMax=3",
        "-L", "127.0.0.1:13000:127.0.0.1:13000",
        "-L", "127.0.0.1:18001:127.0.0.1:18001", "henderson-server1"
    )
    $actualTunnelArguments = Get-TunnelArguments
    Record-SelfTest `
        "tunnel command construction" `
        (($actualTunnelArguments -join [char]0) -ceq ($expectedTunnelArguments -join [char]0)) `
        ($actualTunnelArguments -join " ")

    $expectedActions = @("follow-logs", "logs", "start", "status", "stop")
    $actualActions = @($script:AllowedRemoteActions.Keys | Sort-Object)
    Record-SelfTest `
        "remote action allowlist" `
        (($actualActions -join ",") -ceq ($expectedActions -join ",")) `
        ($actualActions -join ", ")

    $followCommand = Get-RemoteActionTerminalCommand -Action "follow-logs"
    $logsCommand = Get-RemoteActionTerminalCommand -Action "logs"
    Record-SelfTest `
        "follow-logs Ctrl+C cancellation" `
        ($followCommand.Contains('if ($remoteExitCode -eq 130)') -and
            $followCommand.Contains("Live log following stopped by user.") -and
            -not $logsCommand.Contains('if ($remoteExitCode -eq 130)')) `
        "exit 130 is normalized only for follow-logs"

    $testOperationId = [Guid]::Parse("11111111-2222-3333-4444-555555555555")
    $workerCommand = Get-TunnelWorkerInvocationCommand -Action "Status" -OperationId $testOperationId
    Record-SelfTest `
        "background tunnel worker construction" `
        ($workerCommand.Contains("-TunnelWorkerAction 'Status'") -and
            $workerCommand.Contains("-TunnelOperationId '11111111-2222-3333-4444-555555555555'")) `
        $workerCommand

    $controllerText = Get-Content -LiteralPath $PSCommandPath -Raw
    Record-SelfTest `
        "atomic worker completion protocol" `
        ($controllerText.Contains('[Environment]::Exit([int]$workerExitCode)') -and
            $controllerText.Contains('$resultReady = Test-Path -LiteralPath $operation.ResultPath') -and
            $controllerText.Contains('ServerStatusIncluded = $false')) `
        "action results complete before worker exit or optional server refresh"

    Write-Host "SELF-TEST: no SSH connection, tunnel, browser, Docker, or stack action was invoked."
    if ($failures.Count -gt 0) {
        Write-Host "SELF-TEST FAILED: $($failures.Count) check(s) failed."
        return 1
    }

    Write-Host "SELF-TEST PASSED"
    return 0
}

if ($TunnelWorkerAction -ne "None") {
    $workerExitCode = Invoke-TunnelWorkerMode
    [Environment]::Exit([int]$workerExitCode)
}

if ($SelfTest) {
    exit (Invoke-ControllerSelfTest)
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

function Show-OperatorMessage {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Title = "Photo Organizer Development Operator",
        [System.Windows.Forms.MessageBoxIcon]$Icon = [System.Windows.Forms.MessageBoxIcon]::Information
    )

    if ($null -ne $script:ControllerForm -and -not $script:ControllerForm.IsDisposed) {
        [System.Windows.Forms.MessageBox]::Show(
            $script:ControllerForm,
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            $Icon
        ) | Out-Null
    } else {
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            $Icon
        ) | Out-Null
    }
}

function Set-ControllerResult {
    param(
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("SUCCESS", "WARNING", "FAILURE")]
        [string]$Severity = "SUCCESS"
    )

    $script:LastAction = $Action
    $script:LastMessage = $Message
    $script:LastSeverity = $Severity
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Photo Organizer - Development Operator"
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(920, 720)
$form.MinimumSize = New-Object System.Drawing.Size(820, 640)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$script:ControllerForm = $form

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "Photo Organizer Development Operator"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.AutoSize = $true
$titleLabel.Location = New-Object System.Drawing.Point(20, 16)
$form.Controls.Add($titleLabel)

$subtitleLabel = New-Object System.Windows.Forms.Label
$subtitleLabel.Text = "Server: henderson-server1    Repository: /home/chuck/projects/photo-organizer-dev"
$subtitleLabel.AutoSize = $true
$subtitleLabel.Location = New-Object System.Drawing.Point(22, 52)
$form.Controls.Add($subtitleLabel)

$buttonPanel = New-Object System.Windows.Forms.TableLayoutPanel
$buttonPanel.Location = New-Object System.Drawing.Point(20, 82)
$buttonPanel.Size = New-Object System.Drawing.Size(864, 330)
$buttonPanel.ColumnCount = 2
$buttonPanel.RowCount = 6
$buttonPanel.Anchor = "Top,Left,Right"
$buttonPanel.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 50))) | Out-Null
$buttonPanel.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 50))) | Out-Null
for ($row = 0; $row -lt 6; $row++) {
    $buttonPanel.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Percent, 16.6667))) | Out-Null
}
$form.Controls.Add($buttonPanel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Status"
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$statusLabel.AutoSize = $true
$statusLabel.Location = New-Object System.Drawing.Point(20, 426)
$form.Controls.Add($statusLabel)

$statusBox = New-Object System.Windows.Forms.TextBox
$statusBox.Multiline = $true
$statusBox.ReadOnly = $true
$statusBox.ScrollBars = "Vertical"
$statusBox.BackColor = [System.Drawing.Color]::White
$statusBox.ShortcutsEnabled = $true
$statusBox.HideSelection = $false
$statusBox.TabStop = $true
$statusBox.Location = New-Object System.Drawing.Point(20, 454)
$statusBox.Size = New-Object System.Drawing.Size(864, 190)
$statusBox.Anchor = "Top,Bottom,Left,Right"
$form.Controls.Add($statusBox)

$operationProgress = New-Object System.Windows.Forms.ProgressBar
$operationProgress.Location = New-Object System.Drawing.Point(20, 652)
$operationProgress.Size = New-Object System.Drawing.Size(864, 14)
$operationProgress.Anchor = "Bottom,Left,Right"
$operationProgress.Style = [System.Windows.Forms.ProgressBarStyle]::Marquee
$operationProgress.MarqueeAnimationSpeed = 25
$operationProgress.Visible = $false
$form.Controls.Add($operationProgress)

function Format-CachedAvailability {
    param($Value)
    if ($null -eq $Value) {
        return "UNKNOWN"
    }
    return $(if ([bool]$Value) { "True" } else { "False" })
}

function Update-Dashboard {
    $statusBox.Lines = @(
        "Server connection: $($script:CachedServerStatus)",
        "Tunnel: $($script:CachedTunnelStatus)",
        "Local port 13000 available: $(Format-CachedAvailability $script:CachedPort13000Available)",
        "Local port 18001 available: $(Format-CachedAvailability $script:CachedPort18001Available)",
        "Last requested action: $($script:LastAction)",
        "$($script:LastSeverity): $($script:LastMessage)"
    )
}

function Invoke-GuiAction {
    param(
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][scriptblock]$Operation
    )

    try {
        & $Operation
    } catch {
        Set-ControllerResult -Action $Action -Message $_.Exception.Message -Severity "FAILURE"
        Show-OperatorMessage -Message $_.Exception.Message -Title $Action -Icon ([System.Windows.Forms.MessageBoxIcon]::Error)
    }
    Update-Dashboard
}

function Add-OperatorButton {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][int]$Column,
        [Parameter(Mandatory = $true)][int]$Row,
        [Parameter(Mandatory = $true)][scriptblock]$OnClick
    )

    $button = New-Object System.Windows.Forms.Button
    $button.Text = $Text
    $button.Dock = "Fill"
    $button.Margin = New-Object System.Windows.Forms.Padding(6)
    $button.Add_Click($OnClick)
    $buttonPanel.Controls.Add($button, $Column, $Row)

    switch ($Text) {
        "Start Tunnel and Open Photo Organizer" { $script:StartTunnelButton = $button }
        "Open Backend Health" { $script:BackendHealthButton = $button }
        "Stop Tunnel" { $script:StopTunnelButton = $button }
    }
}

$script:StartTunnelButton = $null
$script:BackendHealthButton = $null
$script:StopTunnelButton = $null

function Set-TunnelControlsEnabled {
    param([Parameter(Mandatory = $true)][bool]$Enabled)

    foreach ($button in @(
        $script:StartTunnelButton,
        $script:BackendHealthButton,
        $script:StopTunnelButton
    )) {
        if ($null -ne $button) {
            try {
                $button.Enabled = $Enabled
            } catch {
                # A disposing form must not prevent the remaining controls from being restored.
            }
        }
    }
}

function Remove-TunnelOperationArtifacts {
    param([Parameter(Mandatory = $true)]$Operation)

    foreach ($path in @($Operation.ResultPath, $Operation.TemporaryResultPath)) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
}

function Begin-TunnelOperation {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Start", "Stop", "Status")]
        [string]$WorkerAction,
        [Parameter(Mandatory = $true)][string]$DisplayAction,
        [ValidateSet("None", "OpenFrontend", "OpenBackendHealth")]
        [string]$CompletionBehavior = "None",
        [switch]$Quiet
    )

    if ($null -ne $script:TunnelOperation -or $script:TunnelCompletionInProgress) {
        throw "A tunnel operation is already running."
    }
    if (-not $script:PowerShellExecutable) {
        throw "Windows PowerShell was not found."
    }
    if (-not $script:StateDirectory) {
        throw "LOCALAPPDATA is unavailable; background tunnel status cannot be stored safely."
    }
    if (-not (Test-Path -LiteralPath $script:StateDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $script:StateDirectory -Force | Out-Null
    }

    $operationId = [Guid]::NewGuid()
    $resultPath = Get-TunnelOperationResultPath -OperationId $operationId
    $workerCommand = Get-TunnelWorkerInvocationCommand -Action $WorkerAction -OperationId $operationId
    $encodedCommand = ConvertTo-EncodedPowerShellCommand -Command $workerCommand
    # Do not redirect worker output or error streams; there are no UI-owned pipes to drain or close.
    $workerProcess = Start-Process `
        -FilePath $script:PowerShellExecutable `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-EncodedCommand", $encodedCommand) `
        -WindowStyle Hidden `
        -PassThru

    $script:TunnelOperation = [pscustomobject]@{
        WorkerAction = $WorkerAction
        DisplayAction = $DisplayAction
        CompletionBehavior = $CompletionBehavior
        Quiet = [bool]$Quiet
        Process = $workerProcess
        ResultPath = $resultPath
        TemporaryResultPath = "$resultPath.tmp"
        DeadlineUtc = [DateTime]::UtcNow.AddSeconds(45)
    }

    Set-TunnelControlsEnabled -Enabled $false
    $operationProgress.Visible = $true
    Set-ControllerResult `
        -Action $DisplayAction `
        -Message "Working in the background. Tunnel controls are temporarily disabled." `
        -Severity "WARNING"
    Update-Dashboard
}

function Complete-TunnelOperation {
    if ($form.InvokeRequired) {
        $form.BeginInvoke([System.Windows.Forms.MethodInvoker]{ Complete-TunnelOperation }) | Out-Null
        return
    }
    if ($script:TunnelCompletionInProgress) {
        return
    }

    $operation = $script:TunnelOperation
    if ($null -eq $operation) {
        return
    }

    $resultReady = Test-Path -LiteralPath $operation.ResultPath -PathType Leaf
    $workerExited = $false
    try {
        $operation.Process.Refresh()
        $workerExited = $operation.Process.HasExited
    } catch {
        $workerExited = $true
    }

    $timedOut = (-not $resultReady -and -not $workerExited -and [DateTime]::UtcNow -ge $operation.DeadlineUtc)
    if (-not $resultReady -and -not $workerExited -and -not $timedOut) {
        return
    }

    $script:TunnelCompletionInProgress = $true
    try {
        if ($resultReady -and -not $workerExited) {
            try {
                # The atomic result is authoritative; stop only the directly created PowerShell worker.
                $operation.Process.Kill()
            } catch {
                # The worker normally exits itself immediately after publishing the result.
            }
        }

        if ($timedOut) {
            try {
                $operation.Process.Kill()
            } catch {
                # The directly created worker may already have exited.
            }
            $script:CachedTunnelStatus = "UNKNOWN - background operation timed out"
            $script:CachedTunnelActive = $false
            $script:CachedTunnelPid = $null
            $script:CachedPort13000Available = $null
            $script:CachedPort18001Available = $null
            $script:CachedServerStatus = "UNKNOWN"
            $timeoutMessage = "The background tunnel operation exceeded 45 seconds. A stop was requested only for its controller worker; no SSH tunnel or port owner was assumed or terminated. Reopen the controller to validate state."
            Set-ControllerResult -Action $operation.DisplayAction -Message $timeoutMessage -Severity "FAILURE"
            return
        }

        if (-not $resultReady) {
            throw "The background tunnel worker exited without a result. No tunnel or port-owner state is assumed."
        }

        $result = Get-Content -LiteralPath $operation.ResultPath -Raw -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
        if ([string]$result.Action -ne [string]$operation.WorkerAction) {
            throw "The background tunnel result did not match the requested operation."
        }
        if ([bool]$result.TunnelSnapshotIncluded) {
            $script:CachedTunnelActive = [bool]$result.TunnelActive
            $script:CachedTunnelStatus = [string]$result.TunnelStatus
            $script:CachedTunnelPid = $result.TunnelPid
            $script:CachedPort13000Available = $result.Port13000Available
            $script:CachedPort18001Available = $result.Port18001Available
        }
        if ([bool]$result.ServerStatusIncluded) {
            $script:CachedServerStatus = if ([bool]$result.ServerAvailable) {
                "AVAILABLE - $([string]$result.ServerMessage)"
            } else {
                "UNAVAILABLE - $([string]$result.ServerMessage)"
            }
        }

        $succeeded = [bool]$result.Success
        $message = [string]$result.Message
        $severity = if ($succeeded) { "SUCCESS" } else { "FAILURE" }

        if ($succeeded -and $operation.CompletionBehavior -eq "OpenFrontend") {
            if (-not $script:CachedTunnelActive) {
                $succeeded = $false
                $severity = "FAILURE"
                $message = "Tunnel start returned without a verified active tunnel; the browser was not opened."
            } else {
                try {
                    Start-Process $script:FrontendUrl | Out-Null
                } catch {
                    $succeeded = $false
                    $severity = "FAILURE"
                    $message = "The managed tunnel is active, but the browser could not be opened: $($_.Exception.Message)"
                }
            }
        } elseif ($succeeded -and $operation.CompletionBehavior -eq "OpenBackendHealth") {
            if (-not $script:CachedTunnelActive) {
                $succeeded = $false
                $severity = "WARNING"
                $message = "Start the managed tunnel before opening Backend Health."
            } else {
                try {
                    Start-Process $script:BackendHealthUrl | Out-Null
                    $message = "Opened backend health through the verified managed tunnel."
                } catch {
                    $succeeded = $false
                    $severity = "FAILURE"
                    $message = "The managed tunnel is active, but backend health could not be opened: $($_.Exception.Message)"
                }
            }
        }

        Set-ControllerResult -Action $operation.DisplayAction -Message $message -Severity $severity
    } catch {
        $failureMessage = $_.Exception.Message
        $script:CachedTunnelStatus = "UNKNOWN - background result could not be processed"
        $script:CachedTunnelActive = $false
        $script:CachedTunnelPid = $null
        $script:CachedPort13000Available = $null
        $script:CachedPort18001Available = $null
        Set-ControllerResult -Action $operation.DisplayAction -Message $failureMessage -Severity "FAILURE"
    } finally {
        try {
            Remove-TunnelOperationArtifacts -Operation $operation
        } catch {
            # Artifact cleanup is best effort and must not strand the UI in a busy state.
        }
        try {
            $operation.Process.Dispose()
        } catch {
            # Process cleanup is best effort after completion.
        }

        $script:TunnelOperation = $null
        try {
            $operationProgress.Visible = $false
        } catch {
            # A disposing form needs no progress update.
        }
        try {
            Set-TunnelControlsEnabled -Enabled $true
        } catch {
            # Cleanup continues so the busy-state guard is always cleared.
        }
        try {
            Update-Dashboard
        } catch {
            # Status rendering must not prevent final busy-state cleanup.
        }
        $script:TunnelCompletionInProgress = $false
    }
}

$tunnelOperationTimer = New-Object System.Windows.Forms.Timer
$tunnelOperationTimer.Interval = 250
$tunnelOperationTimer.Add_Tick({ Complete-TunnelOperation })
$tunnelOperationTimer.Start()

Add-OperatorButton -Text "Open Remote VS Code" -Column 0 -Row 0 -OnClick {
    Invoke-GuiAction -Action "Open Remote VS Code" -Operation {
        Open-RemoteVsCode
        Set-ControllerResult -Action "Open Remote VS Code" -Message "Requested the authoritative Remote SSH repository." -Severity "SUCCESS"
    }
}

Add-OperatorButton -Text "Open WinSCP" -Column 1 -Row 0 -OnClick {
    Invoke-GuiAction -Action "Open WinSCP" -Operation {
        Open-WinScpSession
        Set-ControllerResult -Action "Open WinSCP" -Message "Opened the saved henderson-server1 session without initiating a transfer." -Severity "SUCCESS"
    }
}

Add-OperatorButton -Text "Start Development Stack" -Column 0 -Row 1 -OnClick {
    Invoke-GuiAction -Action "Start Development Stack" -Operation {
        Start-VisibleRemoteAction -Action "start"
        Set-ControllerResult -Action "Start Development Stack" -Message "Opened a visible terminal for the fixed start action." -Severity "WARNING"
    }
}

Add-OperatorButton -Text "Stop Development Stack" -Column 1 -Row 1 -OnClick {
    Invoke-GuiAction -Action "Stop Development Stack" -Operation {
        Start-VisibleRemoteAction -Action "stop"
        Set-ControllerResult -Action "Stop Development Stack" -Message "Opened a visible terminal for the fixed stop action." -Severity "WARNING"
    }
}

Add-OperatorButton -Text "Show Stack Status" -Column 0 -Row 2 -OnClick {
    Invoke-GuiAction -Action "Show Stack Status" -Operation {
        Start-VisibleRemoteAction -Action "status"
        Set-ControllerResult -Action "Show Stack Status" -Message "Opened a visible terminal for stack status." -Severity "SUCCESS"
    }
}

Add-OperatorButton -Text "Check Application Health" -Column 1 -Row 2 -OnClick {
    Invoke-GuiAction -Action "Check Application Health" -Operation {
        $result = Invoke-RemoteHealthCheck
        $severity = if ($result.Success) { "SUCCESS" } else { "FAILURE" }
        Set-ControllerResult -Action "Check Application Health" -Message $result.Message -Severity $severity
        $icon = if ($result.Success) { [System.Windows.Forms.MessageBoxIcon]::Information } else { [System.Windows.Forms.MessageBoxIcon]::Error }
        Show-OperatorMessage -Message $result.Message -Title "Application Health" -Icon $icon
    }
}

Add-OperatorButton -Text "Show Recent Logs" -Column 0 -Row 3 -OnClick {
    Invoke-GuiAction -Action "Show Recent Logs" -Operation {
        Start-VisibleRemoteAction -Action "logs"
        Set-ControllerResult -Action "Show Recent Logs" -Message "Opened a visible terminal with a bounded 200-line log tail." -Severity "SUCCESS"
    }
}

Add-OperatorButton -Text "Follow Live Logs" -Column 1 -Row 3 -OnClick {
    Invoke-GuiAction -Action "Follow Live Logs" -Operation {
        Start-VisibleRemoteAction -Action "follow-logs"
        Set-ControllerResult -Action "Follow Live Logs" -Message "Opened live logs; press Ctrl+C in that terminal to stop following." -Severity "WARNING"
    }
}

Add-OperatorButton -Text "Start Tunnel and Open Photo Organizer" -Column 0 -Row 4 -OnClick {
    Invoke-GuiAction -Action "Start Tunnel and Open Photo Organizer" -Operation {
        Begin-TunnelOperation `
            -WorkerAction "Start" `
            -DisplayAction "Start Tunnel and Open Photo Organizer" `
            -CompletionBehavior "OpenFrontend"
    }
}

Add-OperatorButton -Text "Open Backend Health" -Column 1 -Row 4 -OnClick {
    Invoke-GuiAction -Action "Open Backend Health" -Operation {
        if (-not $script:CachedTunnelActive) {
            Set-ControllerResult `
                -Action "Open Backend Health" `
                -Message "Start the managed tunnel before opening Backend Health." `
                -Severity "WARNING"
            return
        }

        Begin-TunnelOperation `
            -WorkerAction "Status" `
            -DisplayAction "Open Backend Health" `
            -CompletionBehavior "OpenBackendHealth"
    }
}

Add-OperatorButton -Text "Stop Tunnel" -Column 0 -Row 5 -OnClick {
    Invoke-GuiAction -Action "Stop Tunnel" -Operation {
        Begin-TunnelOperation -WorkerAction "Stop" -DisplayAction "Stop Tunnel"
    }
}

Add-OperatorButton -Text "Exit" -Column 1 -Row 5 -OnClick {
    $form.Close()
}

$form.Add_FormClosing({
    param($sender, $eventArgs)

    if ($null -ne $script:TunnelOperation) {
        $eventArgs.Cancel = $true
        Set-ControllerResult `
            -Action "Exit" `
            -Message "A tunnel operation is still finishing in the background. Wait for it to complete, then select Exit again." `
            -Severity "WARNING"
        Update-Dashboard
        return
    }

    if ($script:CachedTunnelActive) {
        Show-OperatorMessage `
            -Message "The Photo Organizer tunnel is still active.`r`nUse Stop Tunnel when you are finished." `
            -Title "Tunnel Still Active" `
            -Icon ([System.Windows.Forms.MessageBoxIcon]::Warning)
    }
})

$form.Add_Shown({
    Update-Dashboard
    try {
        Begin-TunnelOperation -WorkerAction "Status" -DisplayAction "Refresh Tunnel Status" -Quiet
    } catch {
        Set-ControllerResult -Action "Refresh Tunnel Status" -Message $_.Exception.Message -Severity "FAILURE"
        Update-Dashboard
    }
})

[void]$form.ShowDialog()
$tunnelOperationTimer.Stop()
$tunnelOperationTimer.Dispose()
