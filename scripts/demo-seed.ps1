# scripts/demo-seed.ps1 — Seed demo database inside docker api container (PowerShell)
# Usage: .\scripts\demo-seed.ps1 [API_BASE_URL]

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ApiBase = if ($args[0]) { $args[0] } else { "http://localhost:8080/api/v1" }
$EnvFile = Join-Path $ProjectRoot ".env.demo"
$ComposeFile = Join-Path $ProjectRoot "docker-compose.demo.yml"

Write-Host "[demo-seed] Seeding database inside the demo api container..." -ForegroundColor Cyan
docker compose -f $ComposeFile --env-file $EnvFile -p sih-demo exec -T api python3 scripts/seed_demo_data.py

Write-Host "[demo-seed] Verifying operator authentication via $ApiBase/auth/login..." -ForegroundColor Cyan

try {
    $loginBody = @{
        username = "operator@weather-platform.gov.in"
        password = "EmergencyOps2026!"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$ApiBase/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 10
    if ($response.access_token) {
        Write-Host "[demo-seed] ✅ Operator authenticated successfully!" -ForegroundColor Green
    } else {
        Write-Host "[demo-seed] ⚠️ Operator login check returned unexpected response." -ForegroundColor Yellow
    }
} catch {
    Write-Host "[demo-seed] ⚠️ Could not verify operator login directly: $_" -ForegroundColor Yellow
}

Write-Host "`n[demo-seed] Seeding complete: operator accounts, relief centers, advisories, and [DEMO] reports created.`n" -ForegroundColor Green
