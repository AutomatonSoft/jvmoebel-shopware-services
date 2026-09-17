"""add contact call fields

Revision ID: b1c4e8a9d2f0
Revises: a8f3d2c1b4e7
Create Date: 2026-09-17 11:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c4e8a9d2f0"
down_revision: Union[str, Sequence[str], None] = "a8f3d2c1b4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contacts",
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "contacts",
        sa.Column("connection_status", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contacts", "connection_status")
    op.drop_column("contacts", "duration_seconds")
