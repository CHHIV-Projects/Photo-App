param(
    [Parameter(Mandatory = $true)]
    [string]$Username
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path
$RuntimeExecutable = Join-Path $ProjectRoot ".tools\icloud_exact_helper\Scripts\icloudpd.exe"

if (-not (Test-Path -LiteralPath $RuntimeExecutable -PathType Leaf)) {
    throw "Helper runtime is not installed. Run bootstrap_icloud_exact_helper.ps1 first."
}

$AuthRoot = $env:PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR
if (-not $AuthRoot) {
    $AuthRoot = Join-Path $env:LOCALAPPDATA "PhotoOrganizer\icloud_exact_helper\auth"
}
New-Item -ItemType Directory -Path $AuthRoot -Force | Out-Null

Write-Host "Authentication is handled by the isolated icloudpd helper."
Write-Host "Photo Organizer does not receive the password, 2FA code, cookies, or session tokens."

& $RuntimeExecutable --password-provider keyring --password-provider console --username $Username --auth-only --cookie-directory $AuthRoot
if ($LASTEXITCODE -ne 0) {
    throw "External iCloud helper authentication did not complete successfully."
}

Write-Host "Isolated helper authentication completed."
