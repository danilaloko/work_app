Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
# Данные для overlay: без этого в onefile в _MEIPASS не будет pics/, QPixmap загрузит пустые картинки.
# Формат PyInstaller: source:dest (см. pyinstaller --help).
& ".\.venv\Scripts\python.exe" -m PyInstaller --clean --windowed --onefile --name presence-desktop `
    --add-data "pics:pics" `
    app.py

Write-Host ""
Write-Host "Windows build is ready:"
Write-Host "$ScriptDir\dist\presence-desktop.exe"
