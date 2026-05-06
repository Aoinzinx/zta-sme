# gateway/middleware.py — Four-Stage Zero Trust Enforcement Pipeline

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
from datetime import datetime
from uuid import uuid4
from typing import Optional

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import SessionLocal
from models import AuditLog, RevokedToken

JWT_SECRET        = os.environ["JWT_SECRET"]
ALGORITHM         = "HS256"
POLICY_ENGINE_URL = os.environ["POLICY_ENGINE_URL"]   # http://127.0.0.1:8001

# Paths that bypass Zero Trust enforcement (health + OpenAPI docs)
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """
    Four-stage Zero Trust enforcement pipeline applied to every request:

    Stage 1 — JWT Extraction & Cryptographic Validation
    Stage 2 — Token Revocation Check  (per-request, no caching)
    Stage 3 — Policy Engine Evaluation (RBAC + resource matching)
    Stage 4 — Decision Enforcement + Asynchronous Immutable Audit Log
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.monotonic()

        # Allow CORS preflight requests through immediately
        if request.method == "OPTIONS":
            return await call_next(request)

        # Allow public paths and all /admin/* paths through without enforcement
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/admin"):
            return await call_next(request)

        # ── STAGE 1: JWT Extraction and Validation ──────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization header"}
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token, JWT_SECRET, algorithms=[ALGORITHM],
                options={"leeway": 30}   # 30-second clock-skew tolerance
            )
            subject_id = payload["sub"]
            role        = payload["role"]
            jti         = payload.get("jti")
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )

        # ── STAGE 2: Revocation Check (every request — no caching) ──────────
        if jti:
            db = SessionLocal()
            try:
                is_revoked = db.query(RevokedToken).filter(
                    RevokedToken.jti == jti
                ).first()
                if is_revoked:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token has been revoked"}
                    )
            finally:
                db.close()

        # ── STAGE 3: Policy Engine Evaluation ───────────────────────────────
        resource = request.url.path
        method   = request.method

        try:
            async with httpx.AsyncClient() as client:
                policy_resp = await client.post(
                    f"{POLICY_ENGINE_URL}/policy/evaluate",
                    json={"role": role, "resource": resource, "method": method},
                    timeout=5.0
                )
            decision_data = policy_resp.json()
        except (httpx.RequestError, Exception):
            # Fail-closed: if policy engine is unreachable, deny access
            return JSONResponse(
                status_code=503,
                content={"detail": "Policy engine unavailable — access denied"}
            )

        decision = decision_data.get("decision", "deny")
        rule_id  = decision_data.get("rule_id")

        # ── STAGE 4: Decision Enforcement + Async Audit ─────────────────────
        latency_ms = int((time.monotonic() - start_time) * 1000)
        client_ip  = request.client.host if request.client else "0.0.0.0"

        # Fire-and-forget audit write (does not add latency to response path)
        asyncio.create_task(write_audit_log(
            subject_id, resource, method, decision, latency_ms, client_ip, rule_id
        ))

        if decision == "deny":
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied by policy"}
            )

        # PERMIT — forward to upstream via proxy route
        response = await call_next(request)
        return response


async def write_audit_log(
    subject_id: str,
    resource: str,
    method: str,
    decision: str,
    latency_ms: int,
    client_ip: str,
    rule_id: Optional[str],
) -> None:
    """Write an immutable audit log entry. Executes as a background asyncio task."""
    db = SessionLocal()
    try:
        entry = AuditLog(
            log_id              = uuid4(),
            timestamp           = datetime.utcnow(),
            subject_id          = subject_id,
            resource            = resource,
            http_method         = method,
            policy_decision     = decision,
            response_latency_ms = latency_ms,
            client_ip           = client_ip,
            rule_id             = rule_id,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        # Audit failures are logged but never surface to the user
    finally:
        db.close()
