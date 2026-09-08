"""add market_code to web facts

Revision ID: c7e4b91a2d10
Revises: 8f3c1a2b0d4e
Create Date: 2026-09-08 08:46:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e4b91a2d10"
down_revision: Union[str, Sequence[str], None] = "8f3c1a2b0d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "product_views",
    "cart_adds",
    "checkouts",
    "payment_method_events",
    "contact_intents",
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        op.add_column(table, sa.Column("market_code", sa.String(length=8), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table in _TABLES:
        op.drop_column(table, "market_code")
