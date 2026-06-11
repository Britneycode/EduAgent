"""chat_sessions 添加置顶字段

Revision ID: 6c8b1176ec54
Revises: 2eeeff12b3fd
Create Date: 2026-04-21 10:01:24.233708

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "6c8b1176ec54"
down_revision: Union[str, Sequence[str], None] = "2eeeff12b3fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}

    if "is_pinned" not in columns:
        op.add_column(
            "chat_sessions",
            sa.Column(
                "is_pinned",
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            ),
        )
    if "pinned_at" not in columns:
        op.add_column(
            "chat_sessions", sa.Column("pinned_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}

    if "pinned_at" in columns:
        op.drop_column("chat_sessions", "pinned_at")
    if "is_pinned" in columns:
        op.drop_column("chat_sessions", "is_pinned")
