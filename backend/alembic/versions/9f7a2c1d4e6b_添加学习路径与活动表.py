"""添加学习路径与活动表

Revision ID: 9f7a2c1d4e6b
Revises: 6c8b1176ec54
Create Date: 2026-04-27 10:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "9f7a2c1d4e6b"
down_revision: Union[str, Sequence[str], None] = "6c8b1176ec54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "learning_paths" not in tables:
        op.create_table(
            "learning_paths",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("goal_topic", sa.String(length=255), nullable=False),
            sa.Column("nodes", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    tables = set(inspect(bind).get_table_names())
    if "learning_activities" not in tables:
        op.create_table(
            "learning_activities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("path_id", sa.Integer(), nullable=True),
            sa.Column("activity_type", sa.String(length=50), nullable=False),
            sa.Column("knowledge_point", sa.String(length=255), nullable=True),
            sa.Column("resource_id", sa.Integer(), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("duration_sec", sa.Integer(), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["path_id"], ["learning_paths.id"]),
            sa.ForeignKeyConstraint(["resource_id"], ["generated_resources.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "learning_activities" in tables:
        op.drop_table("learning_activities")
    tables = set(inspect(bind).get_table_names())
    if "learning_paths" in tables:
        op.drop_table("learning_paths")
