param(
    [string]$Version = "0.5.0"
)

$ErrorActionPreference = "Stop"
$stateRoot = Join-Path $env:LOCALAPPDATA "PhotoOrganizer\WindowsHelper"
$destination = Join-Path (Join-Path $stateRoot "bin") $Version
$scheme = "HKCU:\Software\Classes\photoorganizer-helper"

if (Test-Path -LiteralPath $scheme) {
    Remove-Item -LiteralPath $scheme -Recurse -Force
}
if (Test-Path -LiteralPath $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
}
"WINDOWS_HELPER_UNINSTALL=PASS"
"VERSION_REMOVED=$Version"
"URI_REGISTRATION_REMOVED=True"
"CREDENTIAL_PRESERVED=$([bool](Test-Path -LiteralPath (Join-Path $stateRoot 'credential.dpapi')))"
"STATE_PRESERVED=$([bool](Test-Path -LiteralPath (Join-Path $stateRoot 'helper-state.json')))"
"SERVER_CREDENTIAL_REVOKED=False"
