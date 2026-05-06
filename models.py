# models.py — SQLAlchemy ORM models for all four tables

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Enum, TIMESTAMP
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"

    role_id     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(64), unique=True, nullable=False)
    description = Column(Text)
    users       = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    user_id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username           = Column(String(64), unique=True, nullable=False)
    password_hash      = Column(String(255), nullable=False)
    role_id            = Column(UUID(as_uuid=True), ForeignKey("roles.role_id"), nullable=False)
    is_active          = Column(Boolean, default=True, nullable=False)
    created_at         = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    refresh_token_hash = Column(String(255))    # bcrypt hash of current refresh token
    session_created_at = Column(TIMESTAMP)       # for 8-hour absolute cap enforcement

    role = relationship("Role", back_populates="users")


class Policy(Base):
    __tablename__ = "policies"

    policy_id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_binding     = Column(String(64), nullable=False)
    resource_pattern = Column(String(255), nullable=False)
    http_method      = Column(String(10), nullable=False)
    effect           = Column(Enum("permit", "deny", name="effect_enum"), nullable=False)
    priority         = Column(Integer, default=100, nullable=False)
    is_active        = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp           = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    subject_id          = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    resource            = Column(String(255), nullable=False)
    http_method         = Column(String(10), nullable=False)
    policy_decision     = Column(Enum("permit", "deny", name="decision_enum"), nullable=False)
    response_latency_ms = Column(Integer, nullable=False)
    client_ip           = Column(INET, nullable=False)
    rule_id             = Column(UUID(as_uuid=True))  # which policy rule matched

    __table_args__ = (Index("idx_audit_timestamp", "timestamp"),)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti        = Column(String(255), primary_key=True)  # UUID from JWT jti claim
    revoked_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
