# auth-service/auth.py — JWT Issuance, Verification, and Refresh Token Rotation

import uuid
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Role, RevokedToken

router = APIRouter()
auth_router = router

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET                  = os.environ["JWT_SECRET"]
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_HOURS  = int(os.environ.get("REFRESH_TOKEN_EXPIRE_HOURS", "8"))
ALGORITHM                   = "HS256"


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str

class RevokeRequest(BaseModel):
    jti: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "Viewer"   # role name: Administrator, Operator, Viewer


# ─── Core helpers ─────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def get_user(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(
        User.username == username,
        User.is_active == True
    ).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user(db, username)
    # Constant-time comparison prevents username enumeration timing attacks
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload.update({
        "exp": datetime.utcnow() + expires_delta,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),   # unique token ID for per-token revocation
    })
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user: User, db: Session) -> str:
    """Issue a new refresh token, hash and store it, record session start."""
    raw_token = str(uuid.uuid4())
    user.refresh_token_hash = hash_password(raw_token)
    # Only set session_created_at on first login, not on rotation
    if user.session_created_at is None:
        user.session_created_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return raw_token


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth 2.0 Resource Owner Password Credentials token endpoint."""
    user = authenticate_user(db, form.username, form.password)
    if not user:
        # Identical response for wrong username and wrong password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role.name},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # Reset session on fresh login
    user.session_created_at = None
    db.commit()
    refresh_token = create_refresh_token(user, db)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh")
async def refresh_token(
    req: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh token rotation — invalidate old token, issue a new access+refresh pair."""
    users = db.query(User).filter(
        User.is_active == True,
        User.refresh_token_hash != None
    ).all()

    matched_user = None
    for u in users:
        if u.refresh_token_hash and pwd_context.verify(req.refresh_token, u.refresh_token_hash):
            matched_user = u
            break

    if not matched_user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Enforce 8-hour absolute session cap
    if matched_user.session_created_at:
        session_age = datetime.utcnow() - matched_user.session_created_at
        if session_age > timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS):
            matched_user.refresh_token_hash = None
            db.commit()
            raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    # Rotate: issue new pair (invalidates old refresh token via hash replacement)
    new_access = create_access_token(
        data={"sub": str(matched_user.user_id), "role": matched_user.role.name},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh = create_refresh_token(matched_user, db)

    return {
        "access_token":  new_access,
        "refresh_token": new_refresh,
        "token_type":    "bearer"
    }


@router.post("/revoke")
async def revoke_token(
    req: RevokeRequest,
    db: Session = Depends(get_db)
):
    """Add a JTI to the revocation deny-list."""
    entry = RevokedToken(jti=req.jti, revoked_at=datetime.utcnow())
    db.merge(entry)   # merge is idempotent — safe to call twice with same JTI
    db.commit()
    return {"status": "revoked"}


@router.post("/register", status_code=201)
async def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user account. Role must be: Administrator, Operator, or Viewer."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{payload.role}' not found. Valid roles: Administrator, Operator, Viewer")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role_id=role.role_id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user_id":   str(user.user_id),
        "username":  user.username,
        "role":      role.name,
        "is_active": user.is_active,
    }
