"""add campaign, exceptions, traces, and policies tables

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Campaigns table
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("campaign_id", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("channels", sa.String(255), nullable=False),
        sa.Column("product_focus", sa.String(100), nullable=False),
        sa.Column("urgency", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Campaign exceptions table
    op.create_table(
        "campaign_exceptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("exception_id", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("campaign_id", sa.String(100), index=True, nullable=False),
        sa.Column("exception_type", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="block"),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("violation_detail", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending_review"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Execution traces table
    op.create_table(
        "execution_traces",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("campaign_id", sa.String(100), index=True, nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
    )

    # Policies table
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="block"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("policies")
    op.drop_table("execution_traces")
    op.drop_table("campaign_exceptions")
    op.drop_table("campaigns")
