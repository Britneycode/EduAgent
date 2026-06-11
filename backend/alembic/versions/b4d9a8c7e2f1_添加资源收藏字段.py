"""添加资源收藏字段

Revision ID: b4d9a8c7e2f1
Revises: 9f7a2c1d4e6b
Create Date: 2026-04-29 09:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b4d9a8c7e2f1"
down_revision: Union[str, Sequence[str], None] = "9f7a2c1d4e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("generated_resources")}
    if "is_favorite" not in columns:
        op.add_column(
            "generated_resources",
            sa.Column(
                "is_favorite",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("generated_resources")}
    if "is_favorite" in columns:
        op.drop_column("generated_resources", "is_favorite")
