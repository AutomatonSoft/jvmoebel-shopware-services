import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from core.db.postgres import Base


class AttributionTouch(Base):
    __tablename__ = "attribution_touches"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign: Mapped[str | None] = mapped_column(String(255))
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    gclid: Mapped[str | None] = mapped_column(String(255))
    gbraid: Mapped[str | None] = mapped_column(String(255))
    wbraid: Mapped[str | None] = mapped_column(String(255))
    landing_page: Mapped[str | None] = mapped_column(String(2048))
    referrer: Mapped[str | None] = mapped_column(String(2048))
    is_direct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        Index("ix_attribution_touches_gclid", "gclid"),
        Index("ix_attribution_touches_gbraid", "gbraid"),
        Index("ix_attribution_touches_wbraid", "wbraid"),
        Index("ix_attribution_touches_utm_campaign", "utm_campaign"),
    )


class ProductView(Base):
    __tablename__ = "product_views"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    sku: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    category: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CartAdd(Base):
    __tablename__ = "cart_adds"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    cart_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    sku: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Checkout(Base):
    __tablename__ = "checkouts"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    cart_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentMethodEvent(Base):
    __tablename__ = "payment_method_events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    payment_method: Mapped[str] = mapped_column(String(128), primary_key=True)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    cart_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_stage: Mapped[str | None] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("kind IN ('shown', 'selected', 'failed')", name="ck_payment_method_events_kind"),
    )


class ContactIntent(Base):
    __tablename__ = "contact_intents"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    visitor_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("sessions.session_id"))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str | None] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True, nullable=False)
    lead_id: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("visitors.visitor_id"))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    market_code: Mapped[str | None] = mapped_column(String(8))
    contact_channel: Mapped[str] = mapped_column(String(16), nullable=False)
    contact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tracking_reference: Mapped[str | None] = mapped_column(String(128), index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    product_number: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    lead_id: Mapped[str] = mapped_column(String(32), ForeignKey("leads.lead_id"), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(64), nullable=False)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    order_id: Mapped[str | None] = mapped_column(String(32))
    manual_sale_id: Mapped[str | None] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrderLine(Base):
    __tablename__ = "order_lines"

    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.order_id"), primary_key=True)
    line_item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    is_paid_snapshot: Mapped[bool] = mapped_column(Boolean, primary_key=True)
    product_number: Mapped[str | None] = mapped_column(String(255))
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source_event_type: Mapped[str] = mapped_column(String(64), nullable=False)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.event_id"), unique=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.order_id"), nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(64))
    sales_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    refund_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(128))
    order_state: Mapped[str | None] = mapped_column(String(64))
    payment_state: Mapped[str | None] = mapped_column(String(64))
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefundLine(Base):
    __tablename__ = "refund_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    refund_id: Mapped[str] = mapped_column(String(32), ForeignKey("refunds.refund_id"), nullable=False)
    line_item_id: Mapped[str] = mapped_column(String(32), nullable=False)
    product_number: Mapped[str | None] = mapped_column(String(255))
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
