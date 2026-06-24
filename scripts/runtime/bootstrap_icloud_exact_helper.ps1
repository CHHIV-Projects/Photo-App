param(
    [string]$PythonExecutable = "",
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..")).Path
$RuntimeRoot = Join-Path $ProjectRoot ".tools\icloud_exact_helper"
$RequirementsPath = Join-Path $ScriptRoot "icloud_exact_helper_requirements.txt"

if (-not $PythonExecutable) {
    $PythonExecutable = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Python executable not found: $PythonExecutable"
}

if (-not (Test-Path -LiteralPath $RequirementsPath -PathType Leaf)) {
    throw "Helper requirements manifest not found: $RequirementsPath"
}

$RuntimePython = Join-Path $RuntimeRoot "Scripts\python.exe"

if ($VerifyOnly) {
    if (-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {
        throw "Helper runtime is not installed: $RuntimeRoot"
    }
} elseif (-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $RuntimeRoot) -Force | Out-Null
    & $PythonExecutable -m venv $RuntimeRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create helper runtime."
    }

    & $RuntimePython -m pip install --disable-pip-version-check --no-cache-dir -r $RequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the pinned helper runtime dependencies."
    }
}

& $RuntimePython -c "import importlib.metadata, json; from pyicloud_ipd.services.photos import PhotoAlbum, PhotoAsset; distribution = importlib.metadata.distribution('icloudpd'); direct_url = json.loads(distribution.read_text('direct_url.json') or '{}'); commit = direct_url.get('vcs_info', {}).get('commit_id'); assert distribution.version == '1.32.3', distribution.version; assert commit == '879c561240d993d748ddb4546f935090502b16d3', commit; print('icloud_exact_helper_ready version=' + distribution.version + ' commit=' + commit)"
if ($LASTEXITCODE -ne 0) {
    throw "Helper runtime verification failed."
}

Write-Host "Helper runtime ready: $RuntimeRoot"
