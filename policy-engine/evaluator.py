# policy-engine/evaluator.py — RBAC Rule Matching Algorithm

from fnmatch import fnmatch
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Policy

router = APIRouter()


class PolicyRequest(BaseModel):
    role: str
    resource: str
    method: str


class PolicyDecision(BaseModel):
    decision: str                    # "permit" or "deny"
    rule_id: Optional[str] = None    # UUID of matched rule, or None
    reason: Optional[str]  = None    # "no_matching_rule" if deny-by-default kicked in


@router.post("/evaluate", response_model=PolicyDecision)
async def evaluate(req: PolicyRequest, db: Session = Depends(get_db)):
    """
    Evaluate an access request against active policy rules.

    Algorithm:
    1. Fetch all active rules where role_binding matches the subject's role or '*'
    2. Sort by priority descending (highest priority first)
    3. First rule whose (resource_pattern, http_method) matches wins
    4. If no rule matches → deny by default (Zero Trust principle)
    """
    rules = (
        db.query(Policy)
        .filter(
            Policy.role_binding.in_([req.role, "*"]),
            Policy.is_active == True
        )
        .order_by(Policy.priority.desc())
        .all()
    )

    for rule in rules:
        # fnmatch supports trailing wildcards: /aws/* matches /aws/data
        if fnmatch(req.resource, rule.resource_pattern):
            if rule.http_method in (req.method, "*"):
                return PolicyDecision(
                    decision=rule.effect,
                    rule_id=str(rule.policy_id)
                )

    # No rule matched — Zero Trust deny-by-default
    return PolicyDecision(
        decision="deny",
        rule_id=None,
        reason="no_matching_rule"
    )


@router.get("/rules")
async def list_rules(db: Session = Depends(get_db)):
    """Return all active policy rules (for admin dashboard)."""
    rules = db.query(Policy).filter(Policy.is_active == True).order_by(Policy.priority.desc()).all()
    return [
        {
            "policy_id":        str(r.policy_id),
            "role_binding":     r.role_binding,
            "resource_pattern": r.resource_pattern,
            "http_method":      r.http_method,
            "effect":           r.effect,
            "priority":         r.priority,
        }
        for r in rules
    ]
