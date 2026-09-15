"""initial migration

Revision ID: 8f3c1a2b0d4e
Revises:
Create Date: 2026-08-31 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f3c1a2b0d4e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("domain", sa.String(length=253), nullable=True),
        sa.Column("language", sa.String(length=35), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("cart_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("customer_id", sa.String(length=32), nullable=True),
        sa.Column("order_id", sa.String(length=32), nullable=True),
        sa.Column("contact_id", sa.String(length=32), nullable=True),
        sa.Column("manual_sale_id", sa.String(length=32), nullable=True),
        sa.Column("refund_id", sa.String(length=32), nullable=True),
        sa.Column("aggregate_type", sa.String(length=32), nullable=True),
        sa.Column("aggregate_id", sa.String(length=32), nullable=True),
        sa.Column("aggregate_version", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("consent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_events_customer_id_occurred_at", "events", ["customer_id", "occurred_at"]
    )
    op.create_index(
        "ix_events_lead_id_occurred_at", "events", ["lead_id", "occurred_at"]
    )
    op.create_index(
        "ix_events_order_id_occurred_at", "events", ["order_id", "occurred_at"]
    )
    op.create_index(
        "ix_events_visitor_id_occurred_at", "events", ["visitor_id", "occurred_at"]
    )
    op.create_table(
        "visitors",
        sa.Column("visitor_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "is_stub", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_touch_source", sa.String(length=64), nullable=True),
        sa.Column("first_touch_campaign", sa.String(length=255), nullable=True),
        sa.Column("first_touch_gclid", sa.String(length=255), nullable=True),
        sa.Column("first_touch_gbraid", sa.String(length=255), nullable=True),
        sa.Column("first_touch_wbraid", sa.String(length=255), nullable=True),
        sa.Column("first_touch_utm_source", sa.String(length=255), nullable=True),
        sa.Column("first_touch_utm_medium", sa.String(length=255), nullable=True),
        sa.Column("first_touch_utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("first_touch_utm_content", sa.String(length=255), nullable=True),
        sa.Column("first_touch_utm_term", sa.String(length=255), nullable=True),
        sa.Column("first_touch_landing_page", sa.String(length=2048), nullable=True),
        sa.Column("first_touch_referrer", sa.String(length=2048), nullable=True),
        sa.Column("first_touch_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_touch_sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("last_non_direct_source", sa.String(length=64), nullable=True),
        sa.Column("last_non_direct_campaign", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_gclid", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_gbraid", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_wbraid", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_utm_source", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_utm_medium", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_utm_content", sa.String(length=255), nullable=True),
        sa.Column("last_non_direct_utm_term", sa.String(length=255), nullable=True),
        sa.Column(
            "last_non_direct_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column("last_non_direct_referrer", sa.String(length=2048), nullable=True),
        sa.Column(
            "last_non_direct_occurred_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "last_non_direct_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.PrimaryKeyConstraint("visitor_id"),
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("landing_page", sa.String(length=2048), nullable=True),
        sa.Column("referrer", sa.String(length=2048), nullable=True),
        sa.Column("domain", sa.String(length=253), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_content", sa.String(length=255), nullable=True),
        sa.Column("utm_term", sa.String(length=255), nullable=True),
        sa.Column("gclid", sa.String(length=255), nullable=True),
        sa.Column("gbraid", sa.String(length=255), nullable=True),
        sa.Column("wbraid", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_stub", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.UniqueConstraint("event_id"),
    )
    op.create_table(
        "attribution_touches",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("utm_content", sa.String(length=255), nullable=True),
        sa.Column("utm_term", sa.String(length=255), nullable=True),
        sa.Column("gclid", sa.String(length=255), nullable=True),
        sa.Column("gbraid", sa.String(length=255), nullable=True),
        sa.Column("wbraid", sa.String(length=255), nullable=True),
        sa.Column("landing_page", sa.String(length=2048), nullable=True),
        sa.Column("referrer", sa.String(length=2048), nullable=True),
        sa.Column("is_direct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_attribution_touches_gbraid", "attribution_touches", ["gbraid"])
    op.create_index("ix_attribution_touches_gclid", "attribution_touches", ["gclid"])
    op.create_index(
        "ix_attribution_touches_utm_campaign", "attribution_touches", ["utm_campaign"]
    )
    op.create_index("ix_attribution_touches_wbraid", "attribution_touches", ["wbraid"])
    op.create_table(
        "cart_adds",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("cart_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
    )
    op.create_table(
        "checkouts",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("cart_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
    )
    op.create_table(
        "contact_intents",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
    )
    op.create_table(
        "leads",
        sa.Column("lead_id", sa.String(length=32), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("contact_channel", sa.String(length=16), nullable=True),
        sa.Column("contact_type", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("customer_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("won_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lost_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_stub", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("aggregate_version", sa.Integer(), nullable=True),
        sa.Column("last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attr_first_touch_source", sa.String(length=64), nullable=True),
        sa.Column("attr_first_touch_campaign", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_wbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_source", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_medium", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_first_touch_utm_content", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_term", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column("attr_first_touch_referrer", sa.String(length=2048), nullable=True),
        sa.Column(
            "attr_first_touch_occurred_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "attr_first_touch_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.Column("attr_last_non_direct_source", sa.String(length=64), nullable=True),
        sa.Column(
            "attr_last_non_direct_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_last_non_direct_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_wbraid", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_last_non_direct_utm_source", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_medium", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_content", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_term", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_referrer", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_occurred_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "attr_last_non_direct_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.PrimaryKeyConstraint("lead_id"),
        sa.UniqueConstraint("event_id"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
    )
    op.create_table(
        "payment_method_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("payment_method", sa.String(length=128), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("cart_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_stage", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id", "payment_method"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.CheckConstraint(
            "kind IN ('shown', 'selected', 'failed')",
            name="ck_payment_method_events_kind",
        ),
    )
    op.create_table(
        "product_views",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_table(
        "contacts",
        sa.Column("contact_id", sa.String(length=32), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.String(length=32), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("contact_channel", sa.String(length=16), nullable=False),
        sa.Column("contact_type", sa.String(length=64), nullable=False),
        sa.Column("tracking_reference", sa.String(length=128), nullable=True),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("product_number", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.UniqueConstraint("event_id"),
        sa.PrimaryKeyConstraint("contact_id"),
    )
    op.create_index(
        "ix_contacts_tracking_reference", "contacts", ["tracking_reference"]
    )
    op.create_table(
        "customer_links",
        sa.Column("visitor_id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(length=32), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.PrimaryKeyConstraint("visitor_id", "customer_id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.UniqueConstraint("event_id"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
    )
    op.create_table(
        "lead_status_history",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("lead_id", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=64), nullable=False),
        sa.Column("new_status", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=True),
        sa.Column("manual_sale_id", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
    )
    op.create_table(
        "manual_sales",
        sa.Column("manual_sale_id", sa.String(length=32), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("customer_id", sa.String(length=32), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("amount", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_stub", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("aggregate_version", sa.Integer(), nullable=True),
        sa.Column("last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attr_first_touch_source", sa.String(length=64), nullable=True),
        sa.Column("attr_first_touch_campaign", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_wbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_source", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_medium", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_first_touch_utm_content", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_term", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column("attr_first_touch_referrer", sa.String(length=2048), nullable=True),
        sa.Column(
            "attr_first_touch_occurred_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "attr_first_touch_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.Column("attr_last_non_direct_source", sa.String(length=64), nullable=True),
        sa.Column(
            "attr_last_non_direct_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_last_non_direct_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_wbraid", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_last_non_direct_utm_source", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_medium", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_content", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_term", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_referrer", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_occurred_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "attr_last_non_direct_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.PrimaryKeyConstraint("manual_sale_id"),
        sa.UniqueConstraint("event_id"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
    )
    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(length=32), primary_key=True),
        sa.Column("order_number", sa.String(length=64), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("cart_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("customer_id", sa.String(length=32), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=True),
        sa.Column("market_code", sa.String(length=8), nullable=True),
        sa.Column("payment_method", sa.String(length=128), nullable=True),
        sa.Column("order_state", sa.String(length=64), nullable=True),
        sa.Column("payment_state", sa.String(length=64), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("paid_amount", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aggregate_version", sa.Integer(), nullable=True),
        sa.Column("created_event_id", sa.Uuid(), nullable=True),
        sa.Column("paid_event_id", sa.Uuid(), nullable=True),
        sa.Column(
            "is_stub", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attr_first_touch_source", sa.String(length=64), nullable=True),
        sa.Column("attr_first_touch_campaign", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_wbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_source", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_medium", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_first_touch_utm_content", sa.String(length=255), nullable=True),
        sa.Column("attr_first_touch_utm_term", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_first_touch_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column("attr_first_touch_referrer", sa.String(length=2048), nullable=True),
        sa.Column(
            "attr_first_touch_occurred_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "attr_first_touch_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.Column("attr_last_non_direct_source", sa.String(length=64), nullable=True),
        sa.Column(
            "attr_last_non_direct_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column("attr_last_non_direct_gclid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_gbraid", sa.String(length=255), nullable=True),
        sa.Column("attr_last_non_direct_wbraid", sa.String(length=255), nullable=True),
        sa.Column(
            "attr_last_non_direct_utm_source", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_medium", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_campaign", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_content", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_utm_term", sa.String(length=255), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_landing_page", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_referrer", sa.String(length=2048), nullable=True
        ),
        sa.Column(
            "attr_last_non_direct_occurred_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "attr_last_non_direct_sales_channel_id", sa.String(length=32), nullable=True
        ),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitors.visitor_id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.lead_id"]),
        sa.UniqueConstraint("paid_event_id"),
        sa.ForeignKeyConstraint(["paid_event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.UniqueConstraint("created_event_id"),
        sa.ForeignKeyConstraint(["created_event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("order_id"),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"])
    op.create_table(
        "order_lines",
        sa.Column("order_id", sa.String(length=32), primary_key=True),
        sa.Column("line_item_id", sa.String(length=32), primary_key=True),
        sa.Column("is_paid_snapshot", sa.Boolean(), primary_key=True),
        sa.Column("product_number", sa.String(length=255), nullable=True),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_event_type", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.PrimaryKeyConstraint("order_id", "line_item_id", "is_paid_snapshot"),
    )
    op.create_table(
        "refunds",
        sa.Column("refund_id", sa.String(length=32), primary_key=True),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=True),
        sa.Column("sales_channel_id", sa.String(length=32), nullable=False),
        sa.Column("refund_amount", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("refund_type", sa.String(length=32), nullable=False),
        sa.Column("payment_method", sa.String(length=128), nullable=True),
        sa.Column("order_state", sa.String(length=64), nullable=True),
        sa.Column("payment_state", sa.String(length=64), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("refund_id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.UniqueConstraint("event_id"),
    )
    op.create_table(
        "refund_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("refund_id", sa.String(length=32), nullable=False),
        sa.Column("line_item_id", sa.String(length=32), nullable=False),
        sa.Column("product_number", sa.String(length=255), nullable=True),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=19, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["refund_id"], ["refunds.refund_id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("refund_lines")
    op.drop_table("refunds")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_table("orders")
    op.drop_table("manual_sales")
    op.drop_table("lead_status_history")
    op.drop_table("customer_links")
    op.drop_index("ix_contacts_tracking_reference", table_name="contacts")
    op.drop_table("contacts")
    op.drop_table("product_views")
    op.drop_table("payment_method_events")
    op.drop_table("leads")
    op.drop_table("contact_intents")
    op.drop_table("checkouts")
    op.drop_table("cart_adds")
    op.drop_index("ix_attribution_touches_wbraid", table_name="attribution_touches")
    op.drop_index(
        "ix_attribution_touches_utm_campaign", table_name="attribution_touches"
    )
    op.drop_index("ix_attribution_touches_gclid", table_name="attribution_touches")
    op.drop_index("ix_attribution_touches_gbraid", table_name="attribution_touches")
    op.drop_table("attribution_touches")
    op.drop_table("sessions")
    op.drop_table("visitors")
    op.drop_index("ix_events_visitor_id_occurred_at", table_name="events")
    op.drop_index("ix_events_order_id_occurred_at", table_name="events")
    op.drop_index("ix_events_lead_id_occurred_at", table_name="events")
    op.drop_index("ix_events_customer_id_occurred_at", table_name="events")
    op.drop_table("events")
