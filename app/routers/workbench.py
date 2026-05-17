# app/routers/workbench.py
"""
AI Workbench — Exception management endpoints.

The Workbench is where humans resolve what AI cannot:
- View pending exceptions
- Approve, edit, or reject flagged content
- Track resolution history
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.campaign import CampaignException
from ..security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/workbench", tags=["AI Workbench"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ResolveRequest(BaseModel):
    action: str  # "approve", "edit_approve", "reject"
    resolution_note: str = ""
    edited_content: str = ""


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("")
def list_exceptions(
    status: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all exceptions, optionally filtered by status."""
    query = db.query(CampaignException)

    if status:
        query = query.filter(CampaignException.status == status)

    exceptions = (
        query.order_by(CampaignException.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "exceptions": [
            {
                "id": e.exception_id,
                "campaign_id": e.campaign_id,
                "type": e.exception_type,
                "channel": e.channel,
                "severity": e.severity,
                "content_preview": e.content_preview,
                "violation_detail": e.violation_detail,
                "suggestion": e.suggestion,
                "status": e.status,
                "resolved_by": e.resolved_by,
                "resolution_note": e.resolution_note,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            }
            for e in exceptions
        ],
        "total": query.count(),
        "pending": db.query(CampaignException)
        .filter(CampaignException.status == "pending_review")
        .count(),
    }


@router.get("/{exception_id}")
def get_exception(exception_id: str, db: Session = Depends(get_db)):
    """Get full details of a specific exception."""
    exception = (
        db.query(CampaignException)
        .filter(CampaignException.exception_id == exception_id)
        .first()
    )
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    return {
        "id": exception.exception_id,
        "campaign_id": exception.campaign_id,
        "type": exception.exception_type,
        "channel": exception.channel,
        "severity": exception.severity,
        "content_preview": exception.content_preview,
        "violation_detail": exception.violation_detail,
        "suggestion": exception.suggestion,
        "status": exception.status,
        "resolved_by": exception.resolved_by,
        "resolution_note": exception.resolution_note,
        "created_at": exception.created_at.isoformat() if exception.created_at else None,
        "resolved_at": exception.resolved_at.isoformat() if exception.resolved_at else None,
    }


@router.post("/{exception_id}/resolve")
def resolve_exception(
    exception_id: str,
    request: ResolveRequest,
    db: Session = Depends(get_db),
):
    """
    Resolve an exception.
    Actions: approve (override), edit_approve (fix and approve), reject (discard)
    """
    exception = (
        db.query(CampaignException)
        .filter(CampaignException.exception_id == exception_id)
        .first()
    )
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    if exception.status != "pending_review":
        raise HTTPException(status_code=400, detail="Exception already resolved")

    valid_actions = ["approve", "edit_approve", "reject"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {valid_actions}",
        )

    # Update exception
    if request.action == "approve":
        exception.status = "approved_override"
    elif request.action == "edit_approve":
        exception.status = "approved_edited"
    elif request.action == "reject":
        exception.status = "rejected"

    exception.resolved_by = "admin"  # In production, get from current_user
    exception.resolution_note = request.resolution_note
    exception.resolved_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "id": exception.exception_id,
        "status": exception.status,
        "resolved_at": exception.resolved_at.isoformat(),
        "message": f"Exception {request.action}d successfully",
    }
