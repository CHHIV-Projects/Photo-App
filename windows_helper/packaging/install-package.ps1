param(
    [Parameter(Mandatory = $true)]
    [string]$ArtifactPath,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$ExpectedSha256
)

$ErrorActionPreference = "Stop"
$version = "0.5.0"
$artifact = (Resolve-Path -LiteralPath $ArtifactPath).Path
$actualHash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedSha256.ToLowerInvariant()) {
    throw "Package hash validation failed."
}
$stateRoot = Join-Path $env:LOCALAPPDATA "PhotoOrganizer\WindowsHelper"
$binRoot = Join-Path $stateRoot "bin"
$destination = Join-Path $binRoot $version
$credential = Join-Path $stateRoot "credential.dpapi"
$state = Join-Path $stateRoot "helper-state.json"
$credentialHash = if (Test-Path -LiteralPath $credential -PathType Leaf) { (Get-FileHash -LiteralPath $credential -Algorithm SHA256).Hash } else { $null }
$stateHash = if (Test-Path -LiteralPath $state -PathType Leaf) { (Get-FileHash -LiteralPath $state -Algorithm SHA256).Hash } else { $null }
$staging = Join-Path $binRoot (".staging-" + [guid]::NewGuid().ToString("N"))

if (Test-Path -LiteralPath $destination) {
    throw "The versioned destination already exists."
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null
try {
    Expand-Archive -LiteralPath $artifact -DestinationPath $staging
    $package = Join-Path $staging "PhotoOrganizerWindowsHelper"
    $executable = Join-Path $package "PhotoOrganizerWindowsHelper.exe"
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Package entrypoint is missing."
    }
    Move-Item -LiteralPath $package -Destination $destination
    $installedExecutable = Join-Path $destination "PhotoOrganizerWindowsHelper.exe"
    $scheme = "HKCU:\Software\Classes\photoorganizer-helper"
    $commandKey = Join-Path $scheme "shell\open\command"
    New-Item -Path $commandKey -Force | Out-Null
    New-ItemProperty -Path $scheme -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
    Set-Item -Path $scheme -Value "URL:Photo Organizer Windows Helper"
    Set-Item -Path $commandKey -Value ('"{0}" "%1"' -f $installedExecutable)
    if ($credentialHash -and (Get-FileHash -LiteralPath $credential -Algorithm SHA256).Hash -ne $credentialHash) {
        throw "Protected credential changed unexpectedly."
    }
    if ($stateHash -and (Get-FileHash -LiteralPath $state -Algorithm SHA256).Hash -ne $stateHash) {
        throw "Helper state changed unexpectedly."
    }
    "WINDOWS_HELPER_INSTALL=PASS"
    "HELPER_VERSION=$version"
    "ARTIFACT_SHA256_VALID=True"
    "INSTALL_DESTINATION=$destination"
    "URI_SCHEME=photoorganizer-helper://start"
    "CREDENTIAL_PRESERVED=True"
    "STATE_PRESERVED=True"
    "ADMIN_REQUIRED=False"
    "REPAIRING_PERFORMED=False"
} finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
