"""add agent run events

Revision ID: b9c2d5e6f7a8
Revises: a8f4c9d1e2b3
Create Date: 2026-05-02 16:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b9c2d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a8f4c9d1e2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "agent_run_events" not in tables:
        op.create_table(
            "agent_run_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("agent_name", sa.String(length=100), nullable=False),
            sa.Column("node_name", sa.String(length=100), nullable=False),
            sa.Column("resource_type", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=False),
            sa.Column("llm_provider", sa.String(length=50), nullable=True),
            sa.Column("llm_used", sa.Boolean(), nullable=False),
            sa.Column("input_chars", sa.Integer(), nullable=False),
            sa.Column("output_chars", sa.Integer(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("event_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_agent_run_events_run_id",
            "agent_run_events",
            ["run_id"],
            unique=False,
        )
        op.create_index(
            "ix_agent_run_events_user_created",
            "agent_run_events",
            ["user_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "agent_run_events" in tables:
        op.drop_index("ix_agent_run_events_user_created", table_name="agent_run_events")
        op.drop_index("ix_agent_run_events_run_id", table_name="agent_run_events")
        op.drop_table("agent_run_events")
