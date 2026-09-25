"""add refund invalid_reason

Revision ID: c3e6a1b7d4f2
Revises: b1c4e8a9d2f0
Create Date: 2026-09-24 09:13:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3e6a1b7d4f2"
down_revision: Union[str, Sequence[str], None] = "b1c4e8a9d2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "refunds",
        sa.Column("invalid_reason", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("refunds", "invalid_reason")
