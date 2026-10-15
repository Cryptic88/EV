$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$evDrive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($PSScriptRoot).TrimEnd(':\'))
if ($evDrive.Free -lt 2GB) {
    throw 'Free at least 2 GB on the project drive before installing local speech.'
}
$evPython = Join-Path $PSScriptRoot '.venv-local\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $evPython)) {
    $evRuntime = Join-Path $PSScriptRoot '.runtime\cpython-3.12.15-windows-x86_64-none\python.exe'
    if (Test-Path -LiteralPath $evRuntime) {
        & $evRuntime -m venv .venv-local
    } else {
        & py -3.12 -m venv .venv-local
    }
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 environment creation failed.' }
}
$evUv = Join-Path $PSScriptRoot '.venv\Scripts\uv.exe'
if (Test-Path -LiteralPath $evUv) {
    & $evUv pip install --python $evPython pip -r requirements.txt
} else {
    & $evPython -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $evPython setup_models.py
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
& $evPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Pipeline tests failed.' }
& $evPython verify_local.py
if ($LASTEXITCODE -ne 0) { throw 'Real model verification failed.' }
Write-Host 'E.V. local speech is ready. Run .\start-ev.ps1'
