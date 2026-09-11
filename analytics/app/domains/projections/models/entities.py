import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from core.db.postgres import Base
from domains.projections.models.mixins import AttributionSnapshotMixin, VisitorAttributionMixin


class Visitor(VisitorAttributionMixin, Base):
    __tablename__ = "visitors"

    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    sales_channel_id: Mapped[str | None] = mapped_column(String(32))
    market_code: Mapped[str | None] = mapped_column(String(8))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    landing_page: Mapped[str | None] = mapped_column(String(2048))
    referrer: Mapped[str | None] = mapped_column(String(2048))
    domain: Mapped[str | None] = mapped_column(String(253))
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    gclid: Mapped[str | None] = mapped_column(String(255))
    gbraid: Mapped[str | None] = mapped_column(String(255))
    wbraid: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(64))
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Lead(AttributionSnapshotMixin, Base):
    __tablename__ = "leads"

    lead_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    sales_channel_id: Mapped[str | None] = mapped_column(String(32))
    market_code: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str | None] = mapped_column(String(64))
    contact_channel: Mapped[str | None] = mapped_column(String(16))
    contact_type: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(64))
    customer_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    won_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    aggregate_version: Mapped[int | None] = mapped_column(Integer)
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(AttributionSnapshotMixin, Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_number: Mapped[str | None] = mapped_column(String(64), index=True)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    cart_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    customer_id: Mapped[str | None] = mapped_column(String(32))
    sales_channel_id: Mapped[str | None] = mapped_column(String(32))
    market_code: Mapped[str | None] = mapped_column(String(8))
    payment_method: Mapped[str | None] = mapped_column(String(128))
    order_state: Mapped[str | None] = mapped_column(String(64))
    payment_state: Mapped[str | None] = mapped_column(String(64))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    aggregate_version: Mapped[int | None] = mapped_column(Integer)
    created_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True)
    paid_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True)
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ManualSale(AttributionSnapshotMixin, Base):
    __tablename__ = "manual_sales"

    manual_sale_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"))
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    customer_id: Mapped[str | None] = mapped_column(String(32))
    sales_channel_id: Mapped[str | None] = mapped_column(String(32))
    market_code: Mapped[str | None] = mapped_column(String(8))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    reference: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(64))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    aggregate_version: Mapped[int | None] = mapped_column(Integer)
    last_event_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerLink(Base):
    __tablename__ = "customer_links"

    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True, nullable=False)
    lead_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("leads.lead_id"))
    sales_channel_id: Mapped[str | None] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
