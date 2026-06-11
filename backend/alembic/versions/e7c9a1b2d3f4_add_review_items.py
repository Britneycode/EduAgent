"""add review items

Revision ID: e7c9a1b2d3f4
Revises: d6a2b7c4e9f0
Create Date: 2026-05-01 12:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e7c9a1b2d3f4"
down_revision: Union[str, Sequence[str], None] = "d6a2b7c4e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "review_items" not in tables:
        op.create_table(
            "review_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("resource_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("knowledge_point", sa.String(length=255), nullable=True),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("question_type", sa.String(length=50), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("user_answer", sa.Text(), nullable=False),
            sa.Column("correct_answer", sa.Text(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("review_count", sa.Integer(), nullable=False),
            sa.Column("next_review_at", sa.DateTime(), nullable=True),
            sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["activity_id"], ["learning_activities.id"]),
            sa.ForeignKeyConstraint(["resource_id"], ["generated_resources.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "review_items" in tables:
        op.drop_table("review_items")
