param([switch]$Legacy)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$evPython = Join-Path $PSScriptRoot '.venv-local\Scripts\python.exe'
$evSaved = @{}
if ($Legacy) {
    $evPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $evOverrides = @{TTS_BACKEND='edge'; VAD_BACKEND='energy'; WAKE_BACKEND='vosk'; WHISPER_MODEL_SIZE='base.en'}
    foreach ($evKey in $evOverrides.Keys) {
        $evSaved[$evKey] = [Environment]::GetEnvironmentVariable($evKey, 'Process')
        [Environment]::SetEnvironmentVariable($evKey, $evOverrides[$evKey], 'Process')
    }
}
try {
    if (-not (Test-Path -LiteralPath $evPython)) {
        throw 'Create the Python 3.12 .venv-local environment first; see README.md.'
    }
    & $evPython main.py
} finally {
    foreach ($evKey in $evSaved.Keys) {
        [Environment]::SetEnvironmentVariable($evKey, $evSaved[$evKey], 'Process')
    }
}
