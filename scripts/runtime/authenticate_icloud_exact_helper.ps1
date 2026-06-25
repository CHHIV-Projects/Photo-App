param(
    [Parameter(Mandatory = $true)]
    [string]$Username,

    [switch]$RefreshCredential
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path
$RuntimeExecutable = Join-Path $ProjectRoot ".tools\icloud_exact_helper\Scripts\icloudpd.exe"
$RuntimePython = Join-Path $ProjectRoot ".tools\icloud_exact_helper\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $RuntimeExecutable -PathType Leaf)) {
    throw "Helper runtime is not installed. Run bootstrap_icloud_exact_helper.ps1 first."
}
if ($RefreshCredential -and -not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {
    throw "Helper runtime Python is not installed. Run bootstrap_icloud_exact_helper.ps1 first."
}

$AuthRoot = $env:PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR
if (-not $AuthRoot) {
    $AuthRoot = Join-Path $env:LOCALAPPDATA "PhotoOrganizer\icloud_exact_helper\auth"
}
New-Item -ItemType Directory -Path $AuthRoot -Force | Out-Null

Write-Host "Authentication is handled by the isolated icloudpd helper."
Write-Host "Photo Organizer does not receive the password, 2FA code, cookies, or session tokens."

if ($RefreshCredential) {
    Write-Host "Removing the stored helper keyring credential for the requested account before prompting."
    & $RuntimePython -c "from pyicloud_ipd.utils import delete_password_in_keyring; import sys; delete_password_in_keyring(sys.argv[1])" $Username
    if ($LASTEXITCODE -ne 0) {
        throw "The stored helper keyring credential could not be removed."
    }
}

& $RuntimeExecutable --log-level info --no-progress-bar --password-provider keyring --password-provider console --username $Username --auth-only --cookie-directory $AuthRoot
if ($LASTEXITCODE -ne 0) {
    throw "External iCloud helper authentication did not complete successfully."
}

Write-Host "Isolated helper authentication completed."
