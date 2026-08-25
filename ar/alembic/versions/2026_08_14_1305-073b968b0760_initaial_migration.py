"""initaial migration

Revision ID: 073b968b0760
Revises:
Create Date: 2026-08-14 13:05:19.436258

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "073b968b0760"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "armodels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("width", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("height", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("depth", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit", sa.String(length=1), server_default="m", nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'not_active')", name="ck_ar_models_status"
        ),
        sa.CheckConstraint("depth > 0", name="ck_ar_models_depth_positive"),
        sa.CheckConstraint("height > 0", name="ck_ar_models_height_positive"),
        sa.CheckConstraint("width > 0", name="ck_ar_models_width_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_armodels_sku"), "armodels", ["sku"], unique=True)



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_armodels_sku"), table_name="armodels")
    op.drop_table("armodels")
