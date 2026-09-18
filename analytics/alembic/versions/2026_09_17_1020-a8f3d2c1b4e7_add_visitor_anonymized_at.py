"""add visitor anonymized_at

Revision ID: a8f3d2c1b4e7
Revises: c7e4b91a2d10
Create Date: 2026-09-17 10:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a8f3d2c1b4e7"
down_revision: Union[str, Sequence[str], None] = "c7e4b91a2d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "visitors",
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("visitors", "anonymized_at")
