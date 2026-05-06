# dev_start.ps1
# ---------------------------------------------------------
# One‑command developer start‑up for ZT‑SME Framework on Windows
# ---------------------------------------------------------

# 0. Helper: abort on any error
$ErrorActionPreference = 'Stop'

# 1. Ensure the virtual environment exists and is activated
$VenvPath = "$PSScriptRoot\venv"
if (-Not (Test-Path $VenvPath)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv $VenvPath
}
& "$VenvPath\Scripts\Activate.ps1"

# 2. Upgrade pip and install Python dependencies
Write-Host "Installing/updating Python packages..."
python -m pip install --upgrade pip
pip install -r "$PSScriptRoot\requirements.txt"

# 3. Prepare .env (copy if missing, generate JWT secret if placeholder)
$EnvTemplate = "$PSScriptRoot\.env.example"
$EnvFile     = "$PSScriptRoot\.env"
if (-Not (Test-Path $EnvFile)) {
    Copy-Item $EnvTemplate $EnvFile
    Write-Host ".env created from template; you may need to edit it later."
}
# Replace placeholder secret with a random base64 value
$EnvContent = Get-Content $EnvFile
if ($EnvContent -match "<256-bit random secret") {
    $JwtSecret = [Convert]::ToBase64String((New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes(32))
    (Get-Content $EnvFile) -replace "<256-bit random secret from AWS Secrets Manager>", $JwtSecret | Set-Content $EnvFile
    Write-Host "Generated random JWT_SECRET and updated .env."
}

# 4. PostgreSQL: create role & database if missing
$DbUser = "ztuser"
$DbPass = "CHANGEME"    # Change after first run
$DbName = "ztdb"

Write-Host "Ensuring PostgreSQL role and database exist..."
psql -U postgres -c @"
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DbUser') THEN
      CREATE ROLE $DbUser WITH LOGIN PASSWORD '$DbPass';
   END IF;
END
$$;
"@

psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DbName'" |
    ForEach-Object {
        if ($_ -eq "") {
            psql -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser;"
            Write-Host "Created database $DbName."
        }
    }

# 5. Run Alembic migrations
Write-Host "Applying database migrations..."
cd $PSScriptRoot
alembic upgrade head

# 6. Start FastAPI services as background jobs
$services = @(
    @{ Name = "gateway";       Module = "gateway.main:app";       Port = 8443 }
    @{ Name = "policy-engine"; Module = "policy_engine.main:app"; Port = 8001 }
    @{ Name = "auth-service"; Module = "auth_service.main:app"; Port = 8002 }
)

foreach ($svc in $services) {
    $script = {
        param($module, $port, $venv)
        & "$venv\Scripts\python.exe" -m uvicorn $module --host 0.0.0.0 --port $port --workers 1
    }
    Start-Job -ScriptBlock $script -ArgumentList $svc.Module, $svc.Port, $VenvPath -Name $svc.Name | Out-Null
    Write-Host "Started $($svc.Name) on port $($svc.Port) (background job)."
}

# 7. Start the Next.js dashboard (foreground – you will see its output)
Push-Location "$PSScriptRoot\dashboard"
if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing dashboard NPM dependencies..."
    npm install
}
# Set the gateway URL for the dashboard (adjust if you expose via TLS/domain)
$env:NEXT_PUBLIC_GATEWAY_URL = "http://localhost:8443"
Write-Host "Launching dashboard (http://localhost:3000)..."
npm run dev

# When you exit the dashboard (Ctrl‑C), clean up the FastAPI jobs:
Pop-Location
Write-Host "Stopping FastAPI background jobs..."
Get-Job | Where-Object { $_.Name -in @('gateway','policy-engine','auth-service') } | Remove-Job -Force

Write-Host "All services stopped. Bye!"
