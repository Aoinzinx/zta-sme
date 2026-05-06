# tests/integration_tests.py — 14 functional integration test cases (TC-01 to TC-14)
#
# Run locally:
#   pytest tests/integration_tests.py -v
#
# Environment variables (defaults match local dev setup):
#   GATEWAY_URL   — ZT-SME Gateway  (default: http://127.0.0.1:8443)
#   AUTH_URL      — Auth Service     (default: http://127.0.0.1:8002)
#
# Default credentials come from seed.py:
#   admin    / Admin@1234
#   operator / Operator@1234
#   viewer   / Viewer@1234

import base64
import json
import os
import time
import uuid

import pytest
import requests

GATEWAY  = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8443")
AUTH_URL = os.environ.get("AUTH_URL",    "http://127.0.0.1:8002")

# Seeded credentials (from seed.py)
ADMIN_USER    = os.environ.get("ADMIN_USER",    "admin")
ADMIN_PASS    = os.environ.get("ADMIN_PASS",    "Admin@1234")
OPERATOR_USER = os.environ.get("OPERATOR_USER", "operator")
OPERATOR_PASS = os.environ.get("OPERATOR_PASS", "Operator@1234")
VIEWER_USER   = os.environ.get("VIEWER_USER",   "viewer")
VIEWER_PASS   = os.environ.get("VIEWER_PASS",   "Viewer@1234")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_token(username: str, password: str) -> str:
    r = requests.post(
        f"{AUTH_URL}/auth/token",
        data={"username": username, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    return r.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── TC01–TC05: Core Access Control ──────────────────────────────────────────

class TestCoreAccess:

    def test_tc01_valid_credentials_permit(self):
        """TC01: Valid operator credentials should permit GET /aws/data."""
        token = get_token(OPERATOR_USER, OPERATOR_PASS)
        r = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(token))
        assert r.status_code in (200, 502, 503), f"Expected 200/502/503, got {r.status_code}: {r.text}"

    def test_tc02_invalid_jwt_signature(self):
        """TC02: Tampered JWT signature must be rejected with 401."""
        token = get_token(OPERATOR_USER, OPERATOR_PASS) + "TAMPERED"
        r = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(token))
        assert r.status_code == 401

    def test_tc03_expired_jwt(self):
        """TC03: An expired JWT must be rejected with 401."""
        # Pre-generated token with exp in the past
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiJ0ZXN0Iiwicm9sZSI6Ik9wZXJhdG9yIiwiZXhwIjoxfQ"
            ".INVALIDSIGNATURE"
        )
        r = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(expired_token))
        assert r.status_code == 401

    def test_tc04_insufficient_role_deny(self):
        """TC04: Viewer role must be denied POST /aws/data (only GET permitted)."""
        viewer_token = get_token(VIEWER_USER, VIEWER_PASS)
        r = requests.post(
            f"{GATEWAY}/aws/data",
            headers=auth_header(viewer_token),
            json={"test": "data"},
        )
        assert r.status_code == 403

    def test_tc05_revoked_token(self):
        """TC05: A revoked JTI must be rejected on next use."""
        token = get_token(OPERATOR_USER, OPERATOR_PASS)

        # Decode JTI from the token payload (no signature verification needed here)
        parts   = token.split(".")
        padding = "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(parts[1] + padding))
        jti     = payload["jti"]

        # Revoke the JTI via the auth service
        rev = requests.post(f"{AUTH_URL}/auth/revoke", json={"jti": jti})
        assert rev.status_code == 200

        # Token must now be rejected by the gateway
        r = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(token))
        assert r.status_code == 401


# ─── TC06–TC07: Cross-Cloud Access ───────────────────────────────────────────

class TestCrossCloud:

    def test_tc06_operator_access_azure(self):
        """TC06: Operator accessing Azure backend across hybrid cloud boundary.

        Locally the upstream Azure service is a dummy (502/503 expected).
        On cloud deployment this verifies the proxied response.
        """
        token = get_token(OPERATOR_USER, OPERATOR_PASS)
        r = requests.get(f"{GATEWAY}/azure/data", headers=auth_header(token))
        # Gateway permits the request (policy match); upstream may be unreachable locally
        assert r.status_code in (200, 502, 503), f"Unexpected: {r.status_code}"

    def test_tc07_operator_access_aws(self):
        """TC07: Operator accessing AWS Lambda backend.

        Locally the upstream AWS service is a dummy (502/503 expected).
        On cloud deployment this verifies the proxied response.
        """
        token = get_token(OPERATOR_USER, OPERATOR_PASS)
        r = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(token))
        assert r.status_code in (200, 502, 503), f"Unexpected: {r.status_code}"


# ─── TC08–TC10: Edge Cases ────────────────────────────────────────────────────

class TestEdgeCases:

    def test_tc08_deny_by_default_no_rule(self):
        """TC08: Requests to unconfigured paths must be denied by default."""
        token = get_token(OPERATOR_USER, OPERATOR_PASS)
        r = requests.get(f"{GATEWAY}/nonexistent/path/xyz", headers=auth_header(token))
        assert r.status_code == 403

    def test_tc09_admin_policy_create(self):
        """TC09: Admin can create a new policy rule via the admin API."""
        admin_token = get_token(ADMIN_USER, ADMIN_PASS)
        payload = {
            "role_binding":     "Viewer",
            "resource_pattern": "/reports/*",
            "http_method":      "GET",
            "effect":           "permit",
            "priority":         400,
        }
        r = requests.post(
            f"{GATEWAY}/admin/policies",
            headers=admin_token and auth_header(admin_token),
            json=payload,
        )
        assert r.status_code == 201

    def test_tc10_direct_resource_bypass(self):
        """TC10: Direct call to Lambda API Gateway must be blocked by IP restriction."""
        upstream = "https://<api-id>.execute-api.<region>.amazonaws.com/prod/data"
        try:
            r = requests.get(upstream, timeout=5)
            # If we reach here, expect a 403 from API Gateway resource policy
            assert r.status_code == 403, "IP restriction should have blocked direct access"
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass  # Connection refused / timeout is the expected outcome


# ─── TC11–TC14: Refresh Tokens & Priority ─────────────────────────────────────

class TestRefreshTokens:

    def test_tc11_refresh_token_rotation(self):
        """TC11: Using a refresh token must rotate it; old one must be invalidated."""
        r = requests.post(
            f"{AUTH_URL}/auth/token",
            data={"username": OPERATOR_USER, "password": OPERATOR_PASS},
        )
        original_refresh = r.json()["refresh_token"]

        # Use refresh token once to get a new pair
        r2 = requests.post(f"{AUTH_URL}/auth/refresh", json={"refresh_token": original_refresh})
        assert r2.status_code == 200
        new_refresh = r2.json()["refresh_token"]
        assert new_refresh != original_refresh

        # Attempt to reuse the original refresh token — must be rejected
        r3 = requests.post(f"{AUTH_URL}/auth/refresh", json={"refresh_token": original_refresh})
        assert r3.status_code == 401

    def test_tc12_absolute_session_cap(self):
        """TC12: Sessions older than 8 hours must be rejected.

        Manual test — requires setting session_created_at to 9 hours ago via DB.
        Documented here for completeness; CI skips automatically.
        """
        pytest.skip("Requires DB fixture: set session_created_at = now() - interval '9 hours'")

    def test_tc13_concurrent_login_same_user(self):
        """TC13: Two simultaneous sessions for the same user must both be valid."""
        r1 = requests.post(
            f"{AUTH_URL}/auth/token",
            data={"username": OPERATOR_USER, "password": OPERATOR_PASS},
        )
        r2 = requests.post(
            f"{AUTH_URL}/auth/token",
            data={"username": OPERATOR_USER, "password": OPERATOR_PASS},
        )

        t1 = r1.json()["access_token"]
        t2 = r2.json()["access_token"]
        assert t1 != t2   # tokens must be unique (different jti)

        # Both tokens must be accepted by the gateway
        a1 = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(t1))
        a2 = requests.get(f"{GATEWAY}/aws/data", headers=auth_header(t2))
        assert a1.status_code in (200, 502, 503)
        assert a2.status_code in (200, 502, 503)

    def test_tc14_policy_priority_ordering(self):
        """TC14: A high-priority DENY rule must override a low-priority PERMIT rule."""
        admin_token = get_token(ADMIN_USER, ADMIN_PASS)

        # High-priority deny for Viewer on /test-priority/*
        requests.post(
            f"{GATEWAY}/admin/policies",
            headers=auth_header(admin_token),
            json={
                "role_binding": "Viewer", "resource_pattern": "/test-priority/*",
                "http_method": "GET", "effect": "deny", "priority": 900,
            },
        )

        # Low-priority permit for Viewer on /test-priority/*
        requests.post(
            f"{GATEWAY}/admin/policies",
            headers=auth_header(admin_token),
            json={
                "role_binding": "Viewer", "resource_pattern": "/test-priority/*",
                "http_method": "GET", "effect": "permit", "priority": 100,
            },
        )

        # Viewer must be denied (highest-priority rule wins)
        viewer_token = get_token(VIEWER_USER, VIEWER_PASS)
        r = requests.get(
            f"{GATEWAY}/test-priority/resource",
            headers=auth_header(viewer_token),
        )
        assert r.status_code == 403
