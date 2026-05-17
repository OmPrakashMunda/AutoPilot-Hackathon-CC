# app/routers/seed_policies.py
"""
Seed the database with NovaBrew's default policies.
Run once to populate the policies table.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.policy import Policy

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/seed", tags=["AI Seed"])

NOVABREW_POLICIES = [
    # Banned terms — competitors
    {"name": "competitor", "category": "banned_term", "rule_text": "Sleepy Owl", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Blue Tokai", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Third Wave Coffee", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Starbucks", "severity": "flag"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Nescafe", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Bru", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Country Bean", "severity": "block"},
    {"name": "competitor", "category": "banned_term", "rule_text": "Rage Coffee", "severity": "block"},
    # Banned terms — health claims
    {"name": "health_claim", "category": "banned_term", "rule_text": "cures", "severity": "block"},
    {"name": "health_claim", "category": "banned_term", "rule_text": "heals", "severity": "block"},
    {"name": "health_claim", "category": "banned_term", "rule_text": "boosts immunity", "severity": "block"},
    {"name": "health_claim", "category": "banned_term", "rule_text": "prevents disease", "severity": "block"},
    # Brand voice rules
    {"name": "Brand Voice: Emoji Limit", "category": "brand_voice_rule", "rule_text": "Maximum 2 emojis per post across all channels", "severity": "flag"},
    {"name": "Brand Voice: No ALL CAPS", "category": "brand_voice_rule", "rule_text": "Never use ALL CAPS (3+ consecutive capitalized words)", "severity": "flag"},
    {"name": "Brand Voice: CTA Required", "category": "brand_voice_rule", "rule_text": "Every post must include a Call to Action (CTA) with a link", "severity": "block"},
    {"name": "Brand Voice: Short Sentences", "category": "brand_voice_rule", "rule_text": "Keep sentences under 15 words. Be punchy and direct.", "severity": "flag"},
    {"name": "Brand Voice: No Corporate Tone", "category": "brand_voice_rule", "rule_text": "Never sound corporate or use jargon. Be witty, confident, minimal.", "severity": "flag"},
    # Posting limits
    {"name": "Posting Limit: Daily Cap", "category": "posting_limit", "rule_text": "Maximum 3 posts per channel per day", "severity": "block"},
    {"name": "Posting Limit: Blackout Hours", "category": "posting_limit", "rule_text": "Never schedule posts between 10 PM and 7 AM IST", "severity": "block"},
    {"name": "Posting Limit: No Spam", "category": "posting_limit", "rule_text": "Minimum 2 hours between posts on the same channel", "severity": "flag"},
]


@router.post("")
def seed_policies(db: Session = Depends(get_db)):
    """Seed the database with NovaBrew's default policies. Safe to run multiple times."""
    # Check if already seeded
    existing = db.query(Policy).count()
    if existing > 0:
        return {"message": f"Already seeded ({existing} policies exist)", "seeded": False}

    for p in NOVABREW_POLICIES:
        policy = Policy(
            name=p["name"],
            category=p["category"],
            rule_text=p["rule_text"],
            severity=p["severity"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(policy)

    db.commit()
    return {"message": f"Seeded {len(NOVABREW_POLICIES)} NovaBrew policies", "seeded": True, "count": len(NOVABREW_POLICIES)}
