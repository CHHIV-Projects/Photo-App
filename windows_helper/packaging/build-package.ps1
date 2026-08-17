param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot
)

$ErrorActionPreference = "Stop"
$version = "0.5.0"
$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$output = [System.IO.Path]::GetFullPath($OutputRoot)
$helperRoot = Join-Path $source "windows_helper"
$buildRequirements = Join-Path $helperRoot "packaging\requirements-build.txt"
$spec = Join-Path $helperRoot "packaging\photo_organizer_windows_helper.spec"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("photo-organizer-helper-build-" + [guid]::NewGuid().ToString("N"))
$venv = Join-Path $temporaryRoot "venv"
$python = Join-Path $venv "Scripts\python.exe"
$work = Join-Path $temporaryRoot "work"
$dist = Join-Path $temporaryRoot "dist"
$packageDirectory = Join-Path $dist "PhotoOrganizerWindowsHelper"
$validationDirectory = Join-Path $temporaryRoot "artifact-validation"
$artifact = Join-Path $output "PhotoOrganizerWindowsHelper-$version-win64.zip"

New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
New-Item -ItemType Directory -Force -Path $output | Out-Null
try {
    py -3.11 -m venv $venv
    & $python -m pip install --disable-pip-version-check -r $buildRequirements
    & $python -m pip install --disable-pip-version-check $helperRoot
    & $python -m PyInstaller --clean --noconfirm --workpath $work --distpath $dist $spec
    if (-not (Test-Path -LiteralPath (Join-Path $packageDirectory "PhotoOrganizerWindowsHelper.exe") -PathType Leaf)) {
        throw "Packaged Helper executable was not produced."
    }
    if (Test-Path -LiteralPath $artifact) {
        throw "Artifact path already exists."
    }
    Compress-Archive -LiteralPath $packageDirectory -DestinationPath $artifact -CompressionLevel Optimal
    Expand-Archive -LiteralPath $artifact -DestinationPath $validationDirectory
    $validationExecutable = Join-Path $validationDirectory "PhotoOrganizerWindowsHelper\PhotoOrganizerWindowsHelper.exe"
    if (-not (Test-Path -LiteralPath $validationExecutable -PathType Leaf)) {
        throw "Packaged Helper validation entrypoint was not produced."
    }
    $versionStandardOutput = Join-Path $temporaryRoot "version.stdout"
    $versionStandardError = Join-Path $temporaryRoot "version.stderr"
    $versionProcess = Start-Process `
        -FilePath $validationExecutable `
        -ArgumentList "--version" `
        -WindowStyle Hidden `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $versionStandardOutput `
        -RedirectStandardError $versionStandardError
    $reportedVersion = Get-Content -LiteralPath $versionStandardOutput -Raw
    if ($versionProcess.ExitCode -ne 0 -or -not $reportedVersion -or $reportedVersion.Trim() -ne $version) {
        throw "Packaged Helper version validation failed."
    }
    $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
    $layout = Get-ChildItem -LiteralPath $packageDirectory -File -Recurse |
        ForEach-Object { $_.FullName.Substring($packageDirectory.Length + 1) } |
        Sort-Object
    "WINDOWS_HELPER_BUILD_ONLY=PASS"
    "HELPER_VERSION=$version"
    "PACKAGING_TYPE=PyInstaller one-folder zip"
    "ARTIFACT_PATH=$artifact"
    "ARTIFACT_SHA256=$hash"
    "EXECUTABLE_ENTRYPOINT=PhotoOrganizerWindowsHelper\PhotoOrganizerWindowsHelper.exe"
    "PACKAGED_FILE_COUNT=$($layout.Count)"
    "PACKAGED_LAYOUT_BEGIN"
    $layout
    "PACKAGED_LAYOUT_END"
    "RETAINED_INSTALLATION_CHANGED=False"
    "RETAINED_STATE_CHANGED=False"
    "URI_REGISTRATION_CHANGED=False"
    "PAIRING_CHANGED=False"
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
