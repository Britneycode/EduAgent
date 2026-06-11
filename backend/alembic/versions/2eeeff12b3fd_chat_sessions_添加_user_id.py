"""chat_sessions 添加 user_id

Revision ID: 2eeeff12b3fd
Revises: 8a4a0126e5ed
Create Date: 2026-04-18 22:15:14.318624

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "2eeeff12b3fd"
down_revision: Union[str, Sequence[str], None] = "8a4a0126e5ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    foreign_keys = inspector.get_foreign_keys("chat_sessions")
    has_user_fk = any(
        fk.get("referred_table") == "users" and fk.get("constrained_columns") == ["user_id"]
        for fk in foreign_keys
    )

    with op.batch_alter_table("chat_sessions") as batch_op:
        if "user_id" not in columns:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if not has_user_fk:
            batch_op.create_foreign_key(
                "fk_chat_sessions_user_id", "users", ["user_id"], ["id"]
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    foreign_keys = inspector.get_foreign_keys("chat_sessions")
    has_user_fk = any(
        fk.get("referred_table") == "users" and fk.get("constrained_columns") == ["user_id"]
        for fk in foreign_keys
    )

    with op.batch_alter_table("chat_sessions") as batch_op:
        if has_user_fk:
            batch_op.drop_constraint("fk_chat_sessions_user_id", type_="foreignkey")
        if "user_id" in columns:
            batch_op.drop_column("user_id")
