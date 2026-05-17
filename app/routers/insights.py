# app/routers/insights.py
"""
AI Insights — Aggregated metrics and execution data.

Powers the Insights dashboard with:
- Campaign stats (total, success rate, avg duration)
- Exception stats (caught, resolved, pending)
- Agent performance (per-agent timing)
- Recent activity feed
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.campaign import Campaign, CampaignException, ExecutionTrace
from ..security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/insights", tags=["AI Insights"])


@router.get("")
def get_insights(db: Session = Depends(get_db)):
    """Get aggregated insights for the dashboard."""

    # Campaign stats
    total_campaigns = db.query(Campaign).count()
    completed_campaigns = (
        db.query(Campaign)
        .filter(Campaign.status.in_(["completed", "completed_with_exceptions"]))
        .count()
    )
    failed_campaigns = db.query(Campaign).filter(Campaign.status == "failed").count()

    # Average duration
    avg_duration = db.query(func.avg(Campaign.duration_ms)).scalar() or 0

    # Exception stats
    total_exceptions = db.query(CampaignException).count()
    pending_exceptions = (
        db.query(CampaignException)
        .filter(CampaignException.status == "pending_review")
        .count()
    )
    resolved_exceptions = (
        db.query(CampaignException)
        .filter(CampaignException.status.in_(["approved_override", "approved_edited", "rejected"]))
        .count()
    )

    # Agent performance (average duration per agent)
    agent_stats = (
        db.query(
            ExecutionTrace.agent_name,
            func.avg(ExecutionTrace.duration_ms).label("avg_duration"),
            func.count(ExecutionTrace.id).label("total_calls"),
        )
        .group_by(ExecutionTrace.agent_name)
        .all()
    )

    # Recent campaigns (last 10)
    recent_campaigns = (
        db.query(Campaign)
        .order_by(Campaign.created_at.desc())
        .limit(10)
        .all()
    )

    # Exception breakdown by type
    exception_by_type = (
        db.query(
            CampaignException.exception_type,
            func.count(CampaignException.id).label("count"),
        )
        .group_by(CampaignException.exception_type)
        .all()
    )

    return {
        "campaigns": {
            "total": total_campaigns,
            "completed": completed_campaigns,
            "failed": failed_campaigns,
            "success_rate": round(
                (completed_campaigns / total_campaigns * 100) if total_campaigns > 0 else 0, 1
            ),
            "avg_duration_ms": round(avg_duration, 0),
        },
        "exceptions": {
            "total": total_exceptions,
            "pending": pending_exceptions,
            "resolved": resolved_exceptions,
            "by_type": [
                {"type": t, "count": c} for t, c in exception_by_type
            ],
        },
        "agent_performance": [
            {
                "agent": name,
                "avg_duration_ms": round(avg_dur, 0) if avg_dur else 0,
                "total_calls": total,
            }
            for name, avg_dur, total in agent_stats
        ],
        "recent_campaigns": [
            {
                "campaign_id": c.campaign_id,
                "brief": c.brief[:100],
                "status": c.status,
                "duration_ms": c.duration_ms,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_campaigns
        ],
    }


@router.get("/trace/{campaign_id}")
def get_execution_trace(campaign_id: str, db: Session = Depends(get_db)):
    """Get detailed execution trace for a specific campaign."""
    traces = (
        db.query(ExecutionTrace)
        .filter(ExecutionTrace.campaign_id == campaign_id)
        .order_by(ExecutionTrace.step_number)
        .all()
    )

    if not traces:
        return {"campaign_id": campaign_id, "trace": [], "message": "No trace found"}

    return {
        "campaign_id": campaign_id,
        "trace": [
            {
                "step": t.step_number,
                "agent": t.agent_name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "output_summary": t.output_summary,
            }
            for t in traces
        ],
        "total_duration_ms": sum(t.duration_ms or 0 for t in traces),
    }
