# app/models/campaign.py
"""
Campaign, Exception, and Execution Trace models.
Stores all AI campaign data for the Command Center.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class Campaign(Base):
    """A marketing campaign triggered via the AI Manager."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String(100), unique=True, index=True, nullable=False)
    brief = Column(Text, nullable=False)
    channels = Column(String(255), nullable=False)
    product_focus = Column(String(100), nullable=False)
    urgency = Column(String(20), nullable=False, default="normal")
    status = Column(String(50), nullable=False, default="running")
    result_json = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CampaignException(Base):
    """An exception/violation caught during campaign execution."""

    __tablename__ = "campaign_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String(100), unique=True, index=True, nullable=False)
    campaign_id = Column(String(100), index=True, nullable=False)
    exception_type = Column(String(100), nullable=False)
    channel = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="block")
    content_preview = Column(Text, nullable=True)
    violation_detail = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending_review")
    resolved_by = Column(String(255), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ExecutionTrace(Base):
    """Step-by-step execution trace for a campaign (powers Insights dashboard)."""

    __tablename__ = "execution_traces"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(String(100), index=True, nullable=False)
    step_number = Column(Integer, nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    duration_ms = Column(Float, nullable=True)
    output_summary = Column(Text, nullable=True)
