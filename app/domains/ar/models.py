from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.db.postgres import Base


class ARModel(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    width: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    height: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    depth: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)

    # здесь пока тоже жестко только метры, и Decimal(Numeric), уточнить по тз как надо
    unit: Mapped[str] = mapped_column(String(1), nullable=False, default="m", server_default="m")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)