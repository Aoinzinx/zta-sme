# PowerShell script to set up ZT‑SME Framework on Windows
# ---------------------------------------------------------
# Prerequisites (already installed):
#   • Python 3.12+ (python.exe in PATH)
#   • Node.js 20+   (node & npm in PATH)
#   • PostgreSQL client tools (psql in PATH)
#   • Git (optional, for cloning the repo)

# ---------------------------------------------------------
# 1. Create a virtual environment and install Python deps
$VenvPath = "$PSScriptRoot\venv"
if (-Not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
}

# Activate venv for the rest of the script
& "$VenvPath\Scripts\Activate.ps1"

# Upgrade pip and install requirements
python -m pip install --upgrade pip
pip install -r "$PSScriptRoot\requirements.txt"

# ---------------------------------------------------------
# 2. Prepare .env configuration
$EnvTemplate = "$PSScriptRoot\.env.example"
$EnvFile = "$PSScriptRoot\.env"
if (-Not (Test-Path $EnvFile)) {
    Copy-Item $EnvTemplate $EnvFile
    Write-Host "Copied .env.example to .env. Please edit the file to set your secrets."
}

# Helper to generate a 256‑bit base64 secret if JWT_SECRET is placeholder
$EnvContent = Get-Content $EnvFile
if ($EnvContent -match "<256-bit random secret") {
    $JwtSecret = [Convert]::ToBase64String((New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes(32))
    (Get-Content $EnvFile) -replace "<256-bit random secret from AWS Secrets Manager>", $JwtSecret | Set-Content $EnvFile
    Write-Host "Generated a random JWT_SECRET and updated .env."
}

# ---------------------------------------------------------
# 3. Create PostgreSQL user and database (requires superuser rights)
# Edit the following variables if you changed them in .env
$DbUser = "ztuser"
$DbPass = "CHANGEME"   # replace after first run
$DbName = "ztdb"

# Create user if not exists
psql -U postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DbUser') THEN CREATE ROLE $DbUser WITH LOGIN PASSWORD '$DbPass'; END IF; END $$;"
# Create database if not exists
psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname = '$DbName'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    psql -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser;"
    Write-Host "Created database $DbName."
}

# ---------------------------------------------------------
# 4. Run Alembic migrations
cd $PSScriptRoot
alembic upgrade head

# ---------------------------------------------------------
# 5. Start FastAPI services (gateway, policy-engine, auth-service)
# Each will run in its own PowerShell background job
$services = @(
    @{ Name = "gateway"; Module = "gateway.main:app"; Port = 8443 },
    @{ Name = "policy-engine"; Module = "policy_engine.main:app"; Port = 8001 },
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

# ---------------------------------------------------------
# 6. Install and start the Next.js dashboard
Push-Location "$PSScriptRoot\dashboard"
if (-Not (Test-Path "node_modules")) {
    npm install
}
# Set environment variable for gateway URL (adjust if you use a custom domain)
$gatewayUrl = "http://localhost:8443"
$env:NEXT_PUBLIC_GATEWAY_URL = $gatewayUrl
npm run dev
Pop-Location

# ---------------------------------------------------------
# When you are done, you can stop the services with:
#   Get-Job | Remove-Job -Force
# ---------------------------------------------------------
