# app/routers/policies.py
"""
AI Policies — CRUD for brand safety policies.

Policies are stored both in the local database (for UI display)
and synced to Dropbox CSV files (for the Brand Safety Checker agent to read).
"""

import csv
import io
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.policy import Policy
from ..security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/policies", tags=["AI Policies"])

# Dropbox configuration — update with your token
DROPBOX_ACCESS_TOKEN = ""  # Set in .env or here
DROPBOX_BANNED_TERMS_PATH = "/policies/banned-terms.csv"
DROPBOX_BRAND_RULES_PATH = "/policies/brand-voice-rules.csv"


# =============================================================================
# SCHEMAS
# =============================================================================


class PolicyCreate(BaseModel):
    name: str
    category: str  # "banned_term", "brand_voice_rule", "posting_limit"
    rule_text: str
    severity: str = "block"  # "block", "flag", "warn"
    is_active: bool = True


class PolicyUpdate(BaseModel):
    name: str = None
    rule_text: str = None
    severity: str = None
    is_active: bool = None


# =============================================================================
# HELPER — Sync policies to Dropbox
# =============================================================================


async def sync_banned_terms_to_dropbox(db: Session):
    """
    Sync all active banned_term policies to Dropbox CSV.
    This ensures the Brand Safety Checker always reads the latest policies.
    """
    if not DROPBOX_ACCESS_TOKEN:
        log.warning("DROPBOX_ACCESS_TOKEN not set — skipping Dropbox sync")
        return False

    # Get all active banned terms from DB
    policies = (
        db.query(Policy)
        .filter(Policy.category == "banned_term", Policy.is_active == True)
        .all()
    )

    # Build CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["term", "category", "severity"])
    for p in policies:
        # Parse the rule_text to extract term and subcategory
        writer.writerow([p.rule_text, p.name, p.severity])

    csv_content = output.getvalue().encode("utf-8")

    # Upload to Dropbox
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers={
                    "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
                    "Dropbox-API-Arg": f'{{"path": "{DROPBOX_BANNED_TERMS_PATH}", "mode": "overwrite", "autorename": false}}',
                    "Content-Type": "application/octet-stream",
                },
                content=csv_content,
            )
        if response.status_code == 200:
            log.info("Synced banned terms to Dropbox successfully")
            return True
        else:
            log.error(f"Dropbox sync failed: {response.status_code} — {response.text}")
            return False
    except Exception as e:
        log.error(f"Dropbox sync error: {e}")
        return False


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("")
def list_policies(
    category: str = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all policies, optionally filtered by category."""
    query = db.query(Policy)

    if category:
        query = query.filter(Policy.category == category)
    if active_only:
        query = query.filter(Policy.is_active == True)

    policies = query.order_by(Policy.created_at.desc()).all()

    return {
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "rule_text": p.rule_text,
                "severity": p.severity,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in policies
        ],
        "total": len(policies),
    }


@router.post("")
async def create_policy(request: PolicyCreate, db: Session = Depends(get_db)):
    """Create a new policy and sync to Dropbox."""
    policy = Policy(
        name=request.name,
        category=request.category,
        rule_text=request.rule_text,
        severity=request.severity,
        is_active=request.is_active,
        created_at=datetime.now(timezone.utc),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    # Sync to Dropbox if it's a banned term
    dropbox_synced = False
    if request.category == "banned_term":
        dropbox_synced = await sync_banned_terms_to_dropbox(db)

    return {
        "id": policy.id,
        "name": policy.name,
        "category": policy.category,
        "rule_text": policy.rule_text,
        "severity": policy.severity,
        "is_active": policy.is_active,
        "dropbox_synced": dropbox_synced,
        "message": "Policy created successfully",
    }


@router.put("/{policy_id}")
async def update_policy(
    policy_id: int, request: PolicyUpdate, db: Session = Depends(get_db)
):
    """Update an existing policy and sync to Dropbox."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if request.name is not None:
        policy.name = request.name
    if request.rule_text is not None:
        policy.rule_text = request.rule_text
    if request.severity is not None:
        policy.severity = request.severity
    if request.is_active is not None:
        policy.is_active = request.is_active

    db.commit()

    # Sync to Dropbox
    dropbox_synced = False
    if policy.category == "banned_term":
        dropbox_synced = await sync_banned_terms_to_dropbox(db)

    return {
        "id": policy.id,
        "name": policy.name,
        "status": "updated",
        "dropbox_synced": dropbox_synced,
    }


@router.delete("/{policy_id}")
async def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    """Delete a policy (soft delete — sets is_active to False)."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.is_active = False
    db.commit()

    # Sync to Dropbox
    dropbox_synced = False
    if policy.category == "banned_term":
        dropbox_synced = await sync_banned_terms_to_dropbox(db)

    return {
        "id": policy.id,
        "status": "deleted",
        "dropbox_synced": dropbox_synced,
    }
