$ErrorActionPreference = "Stop"

Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created backend\.env from backend\.env.example"
}

Write-Host "Starting Tax Estimator backend on http://127.0.0.1:8000"
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

