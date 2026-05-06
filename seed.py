# seed.py — Seeds the database with default roles, admin user, and default policies
# Run once: python seed.py

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
from database import SessionLocal, engine
from models import Base, Role, User, Policy

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

try:
    # ── Roles ──────────────────────────────────────────────────────────────────
    roles_data = [
        ("Administrator", "Full system access including user and policy management"),
        ("Operator",      "Read and write access to cloud resources, no admin access"),
        ("Viewer",        "Read-only access to cloud resources"),
    ]
    roles = {}
    for name, desc in roles_data:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=desc)
            db.add(role)
            db.flush()
            print(f"  [+] Role created: {name}")
        else:
            print(f"  [=] Role exists:  {name}")
        roles[name] = role

    db.commit()

    # ── Default admin user ─────────────────────────────────────────────────────
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            password_hash=pwd_context.hash("Admin@1234"),
            role_id=roles["Administrator"].role_id,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("  [+] Admin user created — username: admin  password: Admin@1234")
    else:
        print("  [=] Admin user already exists")

    # ── Default operator user ──────────────────────────────────────────────────
    operator = db.query(User).filter(User.username == "operator").first()
    if not operator:
        operator = User(
            username="operator",
            password_hash=pwd_context.hash("Operator@1234"),
            role_id=roles["Operator"].role_id,
            is_active=True,
        )
        db.add(operator)
        db.commit()
        print("  [+] Operator user created — username: operator  password: Operator@1234")
    else:
        print("  [=] Operator user already exists")

    # ── Default viewer user ────────────────────────────────────────────────────
    viewer = db.query(User).filter(User.username == "viewer").first()
    if not viewer:
        viewer = User(
            username="viewer",
            password_hash=pwd_context.hash("Viewer@1234"),
            role_id=roles["Viewer"].role_id,
            is_active=True,
        )
        db.add(viewer)
        db.commit()
        print("  [+] Viewer user created — username: viewer  password: Viewer@1234")
    else:
        print("  [=] Viewer user already exists")

    # ── Default RBAC policies ──────────────────────────────────────────────────
    policies_data = [
        # Administrator — full access to everything
        ("Administrator", "/aws/*",   "*",      "permit", 1000),
        ("Administrator", "/azure/*", "*",      "permit", 1000),
        ("Administrator", "/admin/*", "*",      "permit", 1000),
        # Operator — GET+POST on cloud resources
        ("Operator",      "/aws/*",   "GET",    "permit", 500),
        ("Operator",      "/aws/*",   "POST",   "permit", 500),
        ("Operator",      "/azure/*", "GET",    "permit", 500),
        ("Operator",      "/azure/*", "POST",   "permit", 500),
        # Viewer — GET only on cloud resources (read-only)
        ("Viewer",        "/aws/*",   "GET",    "permit", 300),
        ("Viewer",        "/azure/*", "GET",    "permit", 300),
        # Explicit deny for Viewer write operations
        ("Viewer",        "/aws/*",   "POST",   "deny",   200),
        ("Viewer",        "/aws/*",   "DELETE", "deny",   200),
        ("Viewer",        "/azure/*", "POST",   "deny",   200),
        ("Viewer",        "/azure/*", "DELETE", "deny",   200),
    ]

    created = 0
    for role_name, pattern, method, effect, priority in policies_data:
        exists = db.query(Policy).filter(
            Policy.role_binding == role_name,
            Policy.resource_pattern == pattern,
            Policy.http_method == method,
            Policy.is_active == True
        ).first()
        if not exists:
            p = Policy(
                role_binding=role_name,
                resource_pattern=pattern,
                http_method=method,
                effect=effect,
                priority=priority,
                is_active=True,
            )
            db.add(p)
            created += 1

    db.commit()
    print(f"  [+] {created} default policies created")
    print("\nSeed complete!")
    print("  Admin login:    username=admin     password=Admin@1234")
    print("  Operator login: username=operator  password=Operator@1234")
    print("  Viewer login:   username=viewer    password=Viewer@1234")

finally:
    db.close()
