#!/usr/bin/env bash
# infra/deploy.sh — EC2 deployment script for ZT-SME Framework
# Run as: bash deploy.sh
# Tested on Ubuntu 24.04 LTS

set -euo pipefail

INSTALL_DIR="/opt/zt-sme-framework"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$INSTALL_DIR/venv"
DB_NAME="ztdb"
DB_USER="ztuser"

echo "=== ZT-SME Framework Deployment ==="

# 1. System dependencies
echo "[1/8] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# 2. Copy application files
echo "[2/8] Copying application files..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$REPO_DIR"/* "$INSTALL_DIR/"
sudo chown -R ubuntu:ubuntu "$INSTALL_DIR"

# 3. Python virtual environment
echo "[3/8] Creating Python virtual environment..."
python3.12 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# 4. PostgreSQL setup
echo "[4/8] Configuring PostgreSQL..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD 'CHANGEME';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
sudo -u postgres psql -c "REVOKE UPDATE, DELETE ON TABLE audit_log FROM $DB_USER;" 2>/dev/null || true

# 5. Database migrations
echo "[5/8] Running Alembic migrations..."
cd "$INSTALL_DIR"
source .env
"$VENV/bin/alembic" upgrade head

# 6. nginx configuration
echo "[6/8] Configuring nginx..."
sudo cp infra/nginx.conf /etc/nginx/sites-available/zt-sme
sudo ln -sf /etc/nginx/sites-available/zt-sme /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 7. systemd services
echo "[7/8] Installing systemd service units..."
sudo cp systemd/zt-policy-engine.service /etc/systemd/system/
sudo cp systemd/zt-auth-service.service   /etc/systemd/system/
sudo cp systemd/zt-gateway.service        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zt-policy-engine zt-auth-service zt-gateway
sudo systemctl start  zt-policy-engine zt-auth-service zt-gateway

# 8. Health checks
echo "[8/8] Running health checks..."
sleep 3
curl -sf http://127.0.0.1:8001/health && echo " Policy Engine: OK"
curl -sf http://127.0.0.1:8002/health && echo " Auth Service:  OK"
curl -sf http://127.0.0.1:8443/health && echo " Gateway:       OK"

echo ""
echo "=== Deployment complete ==="
echo "Configure your .env file at $INSTALL_DIR/.env before use."
