import requests

base_gw   = "http://127.0.0.1:8445"
base_auth = "http://127.0.0.1:8002"
base_pe   = "http://127.0.0.1:8001"

results = []

def chk(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((status, name, detail))
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")

# Health checks
for svc, url in [
    ("Policy Engine", f"{base_pe}/health"),
    ("Auth Service",  f"{base_auth}/health"),
    ("Gateway",       f"{base_gw}/health"),
]:
    try:
        r = requests.get(url, timeout=3)
        chk(f"{svc} /health", r.status_code == 200, str(r.json()))
    except Exception as e:
        chk(f"{svc} /health", False, str(e))

# Admin login
r = requests.post(f"{base_auth}/auth/token",
                  data={"username": "admin", "password": "Admin@1234"}, timeout=5)
chk("Admin login", r.status_code == 200)
admin_token = r.json().get("access_token", "") if r.status_code == 200 else ""

# Bad password rejected
r = requests.post(f"{base_auth}/auth/token",
                  data={"username": "admin", "password": "wrong"}, timeout=5)
chk("Bad password -> 401", r.status_code == 401)

# Dashboard admin endpoints
for path, label in [
    ("/admin/status",   "Status"),
    ("/admin/users",    "Users"),
    ("/admin/policies", "Policies"),
    ("/admin/audit",    "Audit"),
]:
    r = requests.get(f"{base_gw}{path}",
                     headers={"Authorization": f"Bearer {admin_token}"}, timeout=5)
    detail = str(r.json())[:70] if r.status_code == 200 else f"HTTP {r.status_code}"
    chk(f"Admin GET {path}", r.status_code == 200, detail)

# No token -> 401
r = requests.get(f"{base_gw}/aws/data", timeout=3)
chk("No token -> 401", r.status_code == 401)

# Operator login + GET /aws/* -> permit (502 expected, upstream not running)
r = requests.post(f"{base_auth}/auth/token",
                  data={"username": "operator", "password": "Operator@1234"}, timeout=5)
chk("Operator login", r.status_code == 200)
op_token = r.json().get("access_token", "") if r.status_code == 200 else ""
if op_token:
    r = requests.get(f"{base_gw}/aws/data",
                     headers={"Authorization": f"Bearer {op_token}"}, timeout=5)
    chk("Operator GET /aws/* permit (502 ok)", r.status_code in (200, 502),
        f"HTTP {r.status_code}")

# Viewer login
r = requests.post(f"{base_auth}/auth/token",
                  data={"username": "viewer", "password": "Viewer@1234"}, timeout=5)
chk("Viewer login", r.status_code == 200)
vw_token = r.json().get("access_token", "") if r.status_code == 200 else ""

# Viewer POST /aws/* -> deny 403
if vw_token:
    r = requests.post(f"{base_gw}/aws/data",
                      headers={"Authorization": f"Bearer {vw_token}"}, timeout=5)
    chk("Viewer POST /aws/* -> 403", r.status_code == 403, f"HTTP {r.status_code}")

# Favicon no longer 404
r = requests.get(f"{base_gw}/favicon.ico", timeout=3)
chk("Gateway /favicon.ico no 404", r.status_code in (200, 204), f"HTTP {r.status_code}")

# Policy engine direct evaluation
r = requests.post(f"{base_pe}/policy/evaluate",
                  json={"role": "Administrator", "resource": "/aws/data", "method": "GET"},
                  timeout=3)
chk("Policy eval Admin /aws/* GET -> permit",
    r.status_code == 200 and r.json().get("decision") == "permit",
    str(r.json()))

# CORS header on auth service
r = requests.options(f"{base_auth}/auth/token",
                     headers={"Origin": "http://localhost:3001",
                               "Access-Control-Request-Method": "POST"}, timeout=3)
chk("Auth CORS header present",
    "access-control-allow-origin" in r.headers or "access-control-allow-methods" in r.headers)

# Refresh token
if admin_token:
    r_login = requests.post(f"{base_auth}/auth/token",
                            data={"username": "admin", "password": "Admin@1234"}, timeout=5)
    refresh_tok = r_login.json().get("refresh_token", "")
    if refresh_tok:
        r = requests.post(f"{base_auth}/auth/refresh",
                          json={"refresh_token": refresh_tok}, timeout=5)
        chk("Refresh token rotation", r.status_code == 200 and "access_token" in r.json(),
            f"HTTP {r.status_code}")

print()
passed = sum(1 for s, _, _ in results if s == "PASS")
failed = sum(1 for s, _, _ in results if s == "FAIL")
verdict = "ALL SYSTEMS GO" if failed == 0 else "ISSUES REMAIN"
print(f"Result: {passed} PASS  {failed} FAIL  --  {verdict}")
