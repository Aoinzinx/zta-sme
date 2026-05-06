# tests/locustfile.py — Locust performance test harness
#
# Run:
#   locust -f tests/locustfile.py --host https://yourdomain.com \
#          --users 50 --spawn-rate 5 --run-time 60s --headless

import os
import time
from locust import HttpUser, task, between, events

GATEWAY_URL   = os.environ.get("GATEWAY_URL", "https://yourdomain.com")
TEST_USERNAME = os.environ.get("TEST_USERNAME", "test_operator")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass#2024!")


def get_token(client) -> str:
    """Authenticate and return a short-lived access token."""
    resp = client.post(
        "/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


class ZeroTrustUser(HttpUser):
    host      = GATEWAY_URL
    wait_time = between(0.5, 2.0)
    token: str = None

    def on_start(self):
        """Authenticate once before running tasks."""
        self.token = get_token(self.client)

    def _auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def access_aws_resource(self):
        """Primary workload — authorised GET to AWS backend."""
        with self.client.get(
            "/aws/data",
            headers=self._auth_header(),
            name="/aws/data",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 403):
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(5)
    def access_azure_resource(self):
        """Primary workload — authorised GET to Azure backend."""
        with self.client.get(
            "/azure/data",
            headers=self._auth_header(),
            name="/azure/data",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 403):
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def attempt_unauthorised_write(self):
        """Operator/Viewer should receive 403 on POST — validates policy enforcement."""
        with self.client.post(
            "/aws/data",
            headers=self._auth_header(),
            name="/aws/data (deny expected)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 403:
                resp.success()   # 403 is the *expected* outcome here
            else:
                resp.failure(f"Expected 403, got {resp.status_code}")

    @task(1)
    def refresh_token(self):
        """Periodically exercise the token rotation endpoint."""
        # Get a fresh login to obtain a refresh token
        r = self.client.post(
            "/auth/token",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            name="/auth/token (refresh setup)",
        )
        if r.status_code == 200:
            refresh_tok = r.json().get("refresh_token")
            self.client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_tok},
                name="/auth/refresh",
            )
