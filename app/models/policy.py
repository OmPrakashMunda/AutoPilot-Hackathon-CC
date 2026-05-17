# app/models/policy.py
"""
Policy model — stores AI policies for the Brand Safety system.
Policies are synced to Dropbox CSV for the Brand Safety Checker agent.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..core.database import Base


class Policy(Base):
    """An AI policy that governs agent behavior."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    # Categories: "banned_term", "brand_voice_rule", "posting_limit", "custom"
    rule_text = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="block")
    # Severity: "block" (hard stop), "flag" (needs review), "warn" (log only)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
