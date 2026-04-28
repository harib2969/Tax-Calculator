$ErrorActionPreference = "Stop"

$nodePath = "C:\Program Files\nodejs"
if (Test-Path $nodePath) {
  $env:Path = "$nodePath;$env:Path"
  $npmCommand = "$nodePath\npm.cmd"
} else {
  $npmCommand = "npm.cmd"
}

Set-Location "$PSScriptRoot\frontend"

if (-not (Test-Path "node_modules")) {
  Write-Host "Installing frontend packages. This can take a few minutes..."
  & $npmCommand install
}

Write-Host "Starting Tax Estimator frontend on http://localhost:4200"
& $npmCommand start
