$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\python.exe)) {
    & .\setup.ps1
}

Set-Location backend
Write-Host "CampusConnect AI running at http://127.0.0.1:8080"
Write-Host "API docs at http://127.0.0.1:8080/docs"
& ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
