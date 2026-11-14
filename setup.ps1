$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\python.exe)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
.\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (-not (Test-Path backend\.env)) {
    Copy-Item backend\.env.example backend\.env
    Write-Host "Created backend\.env from the example."
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Start the app:  .\run.ps1"
Write-Host "Open:           http://127.0.0.1:8080"
Write-Host "Admin login:    admin@campus.edu / Admin123!"
Write-Host "Student login:  maya@campus.edu / Student123!"
