# Running ZT-SME Framework Locally

This guide explains how to run the ZT-SME Framework (Zero-Trust Security Framework for SMEs) on your local machine.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+** (or 18)
- **Node.js 18+**
- **PowerShell** (for Windows)

## Step 1: Environment Setup

### 1.1 Create .env file
```bash
cp .env.example .env
```

### 1.2 Update .env for local development
Edit `.env` file with these values:
```env
DATABASE_URL=postgresql://ztuser:CHANGEME@localhost:5432/ztdb
JWT_SECRET=your-local-dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_HOURS=8
POLICY_ENGINE_URL=http://127.0.0.1:8001
UPSTREAM_AWS_URL=http://127.0.0.1:9001
UPSTREAM_AZURE_URL=http://127.0.0.1:9002
ENVIRONMENT=development
```

## Step 2: Install Python Dependencies

```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework"
pip install fastapi uvicorn sqlalchemy alembic python-jose passlib python-multipart httpx boto3 pydantic pydantic-settings
```

**Note:** If psycopg2-binary fails, install it separately:
```powershell
pip install psycopg2-binary --no-build-isolation
```

## Step 3: Set Up PostgreSQL

### Option A: Using PostgreSQL Installer (Windows)
1. Download from https://www.postgresql.org/download/windows/
2. Install with password: `postgres`
3. Port: 5432

### Option B: Using Winget
```powershell
winget install PostgreSQL.PostgreSQL.15
```

### Create Database and User
```powershell
# Create database
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -U postgres ztdb

# Create user (run in psql)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE USER ztuser WITH PASSWORD 'CHANGEME';"

# Grant permissions
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE ztdb TO ztdb;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d ztdb -c "GRANT ALL ON SCHEMA public TO ztuser;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d ztdb -c "ALTER SCHEMA public OWNER TO ztuser;"
```

## Step 4: Create Database Tables

```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework"
python -c "from database import engine; from models import Base; Base.metadata.create_all(bind=engine); print('Tables created!')"
```

## Step 5: Start Backend Services

**Open 3 separate terminals and run:**

### Terminal 1: Policy Engine (Port 8001)
```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework\policy-engine"
$env:DATABASE_URL = "postgresql://ztuser:CHANGEME@localhost:5432/ztdb"
$env:JWT_SECRET = "your-local-dev-secret-key-change-in-production"
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

### Terminal 2: Auth Service (Port 8002)
```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework\auth-service"
$env:DATABASE_URL = "postgresql://ztuser:CHANGEME@localhost:5432/ztdb"
$env:JWT_SECRET = "your-local-dev-secret-key-change-in-production"
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

### Terminal 3: Gateway (Port 8443)
```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework\gateway"
$env:DATABASE_URL = "postgresql://ztuser:CHANGEME@localhost:5432/ztdb"
$env:JWT_SECRET = "your-local-dev-secret-key-change-in-production"
$env:POLICY_ENGINE_URL = "http://127.0.0.1:8001"
$env:UPSTREAM_AWS_URL = "http://127.0.0.1:9001"
$env:UPSTREAM_AZURE_URL = "http://127.0.0.1:9002"
python -m uvicorn main:app --host 127.0.0.1 --port 8443
```

## Step 6: Start Dashboard (Frontend)

```powershell
cd "c:\Users\AOIN ZINX\Desktop\bibek21k claude\New folder\zt-sme-framework\dashboard"

# Fix PowerShell execution policy if needed
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Install dependencies
npm install

# Fix tsconfig.json paths (if needed)
# Ensure tsconfig.json has:
# "baseUrl": ".",
# "paths": {
#   "@/*": ["./*"]
# }

# Start dev server
$env:NEXT_PUBLIC_GATEWAY_URL = "http://127.0.0.1:8443"
npm run dev
```

## Verification

### Health Checks
```powershell
# Test Policy Engine
curl http://127.0.0.1:8001/health

# Test Auth Service
curl http://127.0.0.1:8002/health

# Test Gateway
curl http://127.0.0.1:8443/health
```

### API Documentation
- Policy Engine: http://127.0.0.1:8001/docs
- Auth Service: http://127.0.0.1:8002/docs
- Gateway: http://127.0.0.1:8443/docs

### Dashboard
Open http://localhost:3000 in your browser.

## Service Ports Summary

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 3000 | http://localhost:3000 |
| Policy Engine | 8001 | http://127.0.0.1:8001 |
| Auth Service | 8002 | http://127.0.0.1:8002 |
| Gateway | 8443 | http://127.0.0.1:8443 |
| PostgreSQL | 5432 | localhost:5432/ztdb |

## Troubleshooting

### Module Not Found Errors
The services use sys.path modifications to find shared modules. If you see import errors, ensure you're running from the service directories.

### PostgreSQL Connection Issues
- Verify PostgreSQL service is running: `Get-Service -Name "postgresql*"`
- Check authentication: Ensure ztuser has proper permissions
- Verify database exists: `psql -U postgres -c "\l"`

### Dashboard Build Errors
If you see "Module not found: Can't resolve '@/components/Sidebar'":
1. Check `tsconfig.json` has proper `baseUrl` and `paths` configuration
2. Restart the dev server after fixing tsconfig.json

### Port Already in Use
If ports are already in use, either:
- Kill existing processes: `Get-Process -Name "python" | Stop-Process`
- Or use different ports in the uvicorn commands

## Quick Start Script (PowerShell)

```powershell
# Set environment variables
$env:DATABASE_URL = "postgresql://ztuser:CHANGEME@localhost:5432/ztdb"
$env:JWT_SECRET = "your-local-dev-secret-key-change-in-production"
$env:ENVIRONMENT = "development"
$env:POLICY_ENGINE_URL = "http://127.0.0.1:8001"
$env:UPSTREAM_AWS_URL = "http://127.0.0.1:9001"
$env:UPSTREAM_AZURE_URL = "http://127.0.0.1:9002"

# Start all services (run each in separate terminals)
# Terminal 1
python -m uvicorn policy-engine.main:app --host 127.0.0.1 --port 8001

# Terminal 2  
python -m uvicorn auth-service.main:app --host 127.0.0.1 --port 8002

# Terminal 3
python -m uvicorn gateway.main:app --host 127.0.0.1 --port 8443

# Terminal 4 (Dashboard)
cd dashboard
npm run dev
```

## Project Structure

```
zt-sme-framework/
├── policy-engine/     # Policy Decision Point (Port 8001)
├── auth-service/      # Authentication Service (Port 8002)
├── gateway/           # Zero Trust Gateway (Port 8443)
├── dashboard/         # Next.js Admin Dashboard (Port 3000)
├── models.py          # SQLAlchemy ORM models
├── database.py        # Database session management
└── .env               # Environment variables
```

## Default Roles

| Role | AWS Access | Azure Access | Admin |
|------|-----------|--------------|-------|
| Administrator | Full | Full | Yes |
| Operator | GET + POST | GET + POST | No |
| Viewer | GET only | GET only | No |

## Security Notes

- JWT secrets should be changed for production
- PostgreSQL should use strong authentication in production
- The Policy Engine listens on loopback only (127.0.0.1:8001)
- All services should use TLS in production
