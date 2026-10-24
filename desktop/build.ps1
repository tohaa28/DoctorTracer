$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
python -m PyInstaller --noconfirm DoctorTracer.spec --distpath ../rebuilt --workpath ../build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
