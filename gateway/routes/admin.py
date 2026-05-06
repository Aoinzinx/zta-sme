# gateway/routes/admin.py — Admin API (consumed by the Next.js dashboard)
# Access is restricted to the 'Administrator' role by policy rules.

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Role, Policy, AuditLog

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class UserOut(BaseModel):
    user_id:    str
    username:   str
    role:       str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    role:     str = "Viewer"


class PolicyCreate(BaseModel):
    role_binding:     str
    resource_pattern: str
    http_method:      str
    effect:           str   # "permit" | "deny"
    priority:         int = 100


class PolicyOut(PolicyCreate):
    policy_id: str
    is_active: bool

    class Config:
        from_attributes = True


class AuditOut(BaseModel):
    log_id:              str
    timestamp:           datetime
    subject_id:          Optional[str]
    resource:            str
    http_method:         str
    policy_decision:     str
    response_latency_ms: int
    client_ip:           str

    class Config:
        from_attributes = True


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
async def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        UserOut(
            user_id=str(u.user_id),
            username=u.username,
            role=u.role.name,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{payload.role}' not found")
    user = User(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        role_id=role.role_id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(
        user_id=str(user.user_id),
        username=user.username,
        role=role.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.refresh_token_hash = None   # immediately invalidate all sessions
    db.commit()
    return {"status": "deactivated", "user_id": user_id}


# ─── Policies ─────────────────────────────────────────────────────────────────

@router.get("/policies", response_model=List[PolicyOut])
async def list_policies(db: Session = Depends(get_db)):
    policies = db.query(Policy).order_by(Policy.priority.desc()).all()
    return [
        PolicyOut(
            policy_id=str(p.policy_id),
            role_binding=p.role_binding,
            resource_pattern=p.resource_pattern,
            http_method=p.http_method,
            effect=p.effect,
            priority=p.priority,
            is_active=p.is_active,
        )
        for p in policies
    ]


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_policy(payload: PolicyCreate, db: Session = Depends(get_db)):
    if payload.effect not in ("permit", "deny"):
        raise HTTPException(status_code=422, detail="effect must be 'permit' or 'deny'")
    policy = Policy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return PolicyOut(
        policy_id=str(policy.policy_id),
        **payload.model_dump(),
        is_active=True,
    )


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str, db: Session = Depends(get_db)):
    policy = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.is_active = False
    db.commit()
    return {"status": "deactivated", "policy_id": policy_id}


# ─── Audit Log ────────────────────────────────────────────────────────────────

@router.get("/audit", response_model=List[AuditOut])
async def get_audit_log(
    limit: int = Query(100, le=1000),
    offset: int = 0,
    decision: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if decision:
        q = q.filter(AuditLog.policy_decision == decision)
    entries = q.offset(offset).limit(limit).all()
    return [
        AuditOut(
            log_id=str(e.log_id),
            timestamp=e.timestamp,
            subject_id=str(e.subject_id) if e.subject_id else None,
            resource=e.resource,
            http_method=e.http_method,
            policy_decision=e.policy_decision,
            response_latency_ms=e.response_latency_ms,
            client_ip=str(e.client_ip),
        )
        for e in entries
    ]


# ─── Status ───────────────────────────────────────────────────────────────────

@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    total_users    = db.query(User).count()
    active_users   = db.query(User).filter(User.is_active == True).count()
    total_policies = db.query(Policy).filter(Policy.is_active == True).count()
    total_requests = db.query(AuditLog).count()
    denied         = db.query(AuditLog).filter(AuditLog.policy_decision == "deny").count()

    return {
        "users":        {"total": total_users, "active": active_users},
        "policies":     {"active": total_policies},
        "requests":     {"total": total_requests, "denied": denied},
        "deny_rate_pct": round(denied / total_requests * 100, 2) if total_requests else 0,
    }
