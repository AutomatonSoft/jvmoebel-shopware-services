import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db.postgres import Base


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    market_code: Mapped[str | None] = mapped_column(String(8))
    domain: Mapped[str | None] = mapped_column(String(253))
    language: Mapped[str | None] = mapped_column(String(35))
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    cart_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    lead_id: Mapped[str | None] = mapped_column(String(32))
    customer_id: Mapped[str | None] = mapped_column(String(32))
    order_id: Mapped[str | None] = mapped_column(String(32))
    contact_id: Mapped[str | None] = mapped_column(String(32))
    manual_sale_id: Mapped[str | None] = mapped_column(String(32))
    refund_id: Mapped[str | None] = mapped_column(String(32))
    aggregate_type: Mapped[str | None] = mapped_column(String(32))
    aggregate_id: Mapped[str | None] = mapped_column(String(32))
    aggregate_version: Mapped[int | None] = mapped_column(Integer)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    consent: Mapped[dict | None] = mapped_column(JSONB)
    body: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_events_visitor_id_occurred_at", "visitor_id", "occurred_at"),
        Index("ix_events_lead_id_occurred_at", "lead_id", "occurred_at"),
        Index("ix_events_order_id_occurred_at", "order_id", "occurred_at"),
        Index("ix_events_customer_id_occurred_at", "customer_id", "occurred_at"),
    )
