"""add course id to wiki entries

Revision ID: a8f4c9d1e2b3
Revises: e7c9a1b2d3f4
Create Date: 2026-05-02 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "a8f4c9d1e2b3"
down_revision: Union[str, Sequence[str], None] = "e7c9a1b2d3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wiki_entries")}
    if "course_id" not in columns:
        op.add_column(
            "wiki_entries",
            sa.Column("course_id", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("wiki_entries")}
    if "course_id" in columns:
        op.drop_column("wiki_entries", "course_id")
