"""add profile snapshots

Revision ID: d6a2b7c4e9f0
Revises: b4d9a8c7e2f1
Create Date: 2026-04-30 11:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d6a2b7c4e9f0"
down_revision: Union[str, Sequence[str], None] = "b4d9a8c7e2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "profile_snapshots" not in tables:
        op.create_table(
            "profile_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=30), nullable=False),
            sa.Column("changed_fields", sa.JSON(), nullable=False),
            sa.Column("profile_data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_profile_snapshots_user_id",
            "profile_snapshots",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "profile_snapshots" in tables:
        op.drop_index("ix_profile_snapshots_user_id", table_name="profile_snapshots")
        op.drop_table("profile_snapshots")
