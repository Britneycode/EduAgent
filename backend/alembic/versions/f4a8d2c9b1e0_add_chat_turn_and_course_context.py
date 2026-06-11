"""add chat turn and course context

Revision ID: f4a8d2c9b1e0
Revises: b9c2d5e6f7a8
Create Date: 2026-05-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "f4a8d2c9b1e0"
down_revision: Union[str, Sequence[str], None] = "b9c2d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    chat_session_columns = _columns("chat_sessions")
    if "course_id" not in chat_session_columns:
        op.add_column(
            "chat_sessions",
            sa.Column("course_id", sa.String(length=100), nullable=True),
        )

    chat_message_columns = _columns("chat_messages")
    if "turn_id" not in chat_message_columns:
        op.add_column(
            "chat_messages",
            sa.Column("turn_id", sa.String(length=64), nullable=True),
        )

    generated_resource_columns = _columns("generated_resources")
    if "turn_id" not in generated_resource_columns:
        op.add_column(
            "generated_resources",
            sa.Column("turn_id", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    generated_resource_columns = _columns("generated_resources")
    if "turn_id" in generated_resource_columns:
        op.drop_column("generated_resources", "turn_id")

    chat_message_columns = _columns("chat_messages")
    if "turn_id" in chat_message_columns:
        op.drop_column("chat_messages", "turn_id")

    chat_session_columns = _columns("chat_sessions")
    if "course_id" in chat_session_columns:
        op.drop_column("chat_sessions", "course_id")
