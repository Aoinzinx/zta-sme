# ZT-SME Framework
### A Lightweight Zero-Trust Security Framework for Nepali SMEs on AWS–Azure Hybrid Clouds

**Student:** Bibek Kumar Katwal | ID: 23056296  
**Module:** FC7P01NI — Level 7 Project | London Metropolitan University  
**Supervisor:** Mr Rajesh Chhetry

---

## Architecture Overview

```
Internet ──► nginx (TLS) ──► Zero Trust Gateway (8443)
                                 │
                    ┌────────────┤
                    │            │
             AWS Lambda      Azure App Service
             (financial)     (subscriptions)
                    │            │
              Policy Engine (8001) ◄─── RBAC evaluation
              Auth Service  (8002) ◄─── JWT issuance
              PostgreSQL           ◄─── Users, policies, audit
```

The **four-stage Zero Trust pipeline** runs on every request:
1. **JWT validation** — cryptographic signature + expiry
2. **Revocation check** — per-request JTI lookup (no caching)
3. **Policy evaluation** — RBAC rules via Policy Engine
4. **Enforcement + audit** — deny/permit + immutable log entry

---

## Project Structure

```
zt-sme-framework/
├── gateway/          # Zero Trust Access Gateway (FastAPI, port 8443)
├── policy-engine/    # Policy Decision Point     (FastAPI, port 8001)
├── auth-service/     # Authentication Service    (FastAPI, port 8002)
├── dashboard/        # Admin Dashboard           (Next.js 14)
├── infra/
│   ├── aws-lambda/   # Lambda demonstration service
│   ├── azure-app/    # Azure Express demo service
│   ├── nginx.conf    # TLS reverse proxy
│   └── deploy.sh     # EC2 one-command deployment
├── tests/
│   ├── locustfile.py         # Load test (50 VUs)
│   └── integration_tests.py  # 14 functional test cases
├── systemd/          # systemd service units
├── alembic/          # Database migrations
├── models.py         # SQLAlchemy ORM (shared)
├── database.py       # Session management (shared)
└── requirements.txt
```

---

## Quick Start (EC2)

```bash
# 1. Clone and configure
git clone <repo> zt-sme-framework
cd zt-sme-framework
cp .env.example .env
# Edit .env — fill in JWT_SECRET, DATABASE_URL, upstream URLs

# 2. Deploy (Ubuntu 24.04)
bash infra/deploy.sh

# 3. Obtain TLS certificate
sudo certbot --nginx -d yourdomain.com

# 4. Run integration tests
pip install pytest requests
GATEWAY_URL=https://yourdomain.com pytest tests/integration_tests.py -v
```

---

## Default Roles & Policies

| Role          | AWS Access | Azure Access | Admin |
|---------------|-----------|-------------|-------|
| Administrator | Full      | Full        | Yes   |
| Operator      | GET + POST| GET + POST  | No    |
| Viewer        | GET only  | GET only    | No    |

All other paths are **denied by default** (Zero Trust principle).

---

## Running Tests

```bash
# Functional tests (14 cases, TC01–TC14)
pytest tests/integration_tests.py -v

# Load test (50 concurrent users, 60 seconds)
locust -f tests/locustfile.py --host https://yourdomain.com \
       --users 50 --spawn-rate 5 --run-time 60s --headless
```

---

## Dashboard

The Next.js admin dashboard runs separately and connects to the Gateway admin API:

```bash
cd dashboard
npm install
NEXT_PUBLIC_GATEWAY_URL=https://yourdomain.com npm run dev
```

Pages: **Status** · **Users** · **Policies** · **Audit Log**

---

## Security Notes

- JWT secrets are loaded from AWS Secrets Manager at startup — never committed to version control
- The audit log table has `UPDATE` and `DELETE` revoked from the application DB user
- The Policy Engine listens on loopback only (`127.0.0.1:8001`) — never externally exposed
- The Lambda API Gateway resource policy restricts invocations to the Gateway's Elastic IP
- nginx enforces TLS 1.2/1.3 and rate-limits to 100 req/s per IP
