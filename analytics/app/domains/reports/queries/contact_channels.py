from collections import defaultdict

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Lead, ManualSale, Order, Visitor
from domains.projections.models.facts import Contact, ContactIntent, Refund
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_currency,
    apply_matching_order_currency,
    apply_payment_method,
    apply_period_channel_market,
    apply_snapshot_attr,
    apply_visitor_attr,
    format_rate,
)
from domains.reports.money_agg import (
    add_to_money,
    empty_money_buckets,
    money_breakdowns,
)
from domains.reports.schemas import ContactChannelRow, ContactChannelsResponse


def _empty_channel() -> dict:
    return {
        "intents": 0,
        "contacts": 0,
        "leads_from_contacts": 0,
        "leads": 0,
        "orders_paid": 0,
        "manual_sales": 0,
        "converting_leads": 0,
        "money": empty_money_buckets(),
    }


def _apply_channel(stmt, column, filters: ReportFilters):
    if filters.channel is None:
        return stmt
    return stmt.where(column == filters.channel)


def _apply_contact_filters(stmt, filters: ReportFilters):
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Contact.occurred_at,
        sales_channel_id=Contact.sales_channel_id,
        market_code=Contact.market_code,
    )
    stmt = _apply_channel(stmt, Contact.contact_channel, filters)
    if filters.source is not None or filters.campaign is not None:
        stmt = stmt.join(Lead, Contact.lead_id == Lead.lead_id)
        stmt = apply_snapshot_attr(stmt, Lead, filters)
    return stmt


def _paid_order_exists(filters: ReportFilters):
    conditions = [
        Order.lead_id == Lead.lead_id,
        Order.paid_event_id.isnot(None),
    ]
    if filters.payment_method is not None:
        conditions.append(Order.payment_method == filters.payment_method)
    if filters.currency is not None:
        conditions.append(Order.currency == filters.currency)
    return exists().where(*conditions)


def _confirmed_manual_sale_exists(filters: ReportFilters):
    conditions = [
        ManualSale.lead_id == Lead.lead_id,
        ManualSale.event_id.isnot(None),
        ManualSale.cancelled_at.is_(None),
    ]
    if filters.currency is not None:
        conditions.append(ManualSale.currency == filters.currency)
    return exists().where(*conditions)


async def query_contact_channels(
    session: AsyncSession,
    filters: ReportFilters,
) -> ContactChannelsResponse:
    items: dict[str, dict] = defaultdict(_empty_channel)

    intent_stmt = (
        select(ContactIntent.channel, func.count())
        .select_from(ContactIntent)
        .join(Visitor, ContactIntent.visitor_id == Visitor.visitor_id)
        .where(Visitor.is_stub.is_(False))
        .group_by(ContactIntent.channel)
    )
    intent_stmt = apply_period_channel_market(
        intent_stmt,
        filters,
        occurred_at=ContactIntent.occurred_at,
        sales_channel_id=ContactIntent.sales_channel_id,
        market_code=ContactIntent.market_code,
    )
    intent_stmt = apply_visitor_attr(
        intent_stmt,
        filters,
        visitor_joined=True,
        visitor_id_col=ContactIntent.visitor_id,
    )
    intent_stmt = _apply_channel(intent_stmt, ContactIntent.channel, filters)
    intents = await session.execute(intent_stmt)
    for channel, count in intents.all():
        items[str(channel)]["intents"] = int(count or 0)

    contact_stmt = (
        select(Contact.contact_channel, func.count())
        .select_from(Contact)
        .group_by(Contact.contact_channel)
    )
    contact_stmt = _apply_contact_filters(contact_stmt, filters)
    contacts = await session.execute(contact_stmt)
    for channel, count in contacts.all():
        items[str(channel)]["contacts"] = int(count or 0)

    contact_leads_stmt = (
        select(
            Contact.contact_channel,
            func.count(func.distinct(Contact.lead_id)),
        )
        .select_from(Contact)
        .group_by(Contact.contact_channel)
    )
    contact_leads_stmt = _apply_contact_filters(contact_leads_stmt, filters)
    contact_leads = await session.execute(contact_leads_stmt)
    for channel, count in contact_leads.all():
        items[str(channel)]["leads_from_contacts"] = int(count or 0)

    lead_stmt = (
        select(Lead.contact_channel, func.count())
        .select_from(Lead)
        .where(Lead.event_id.isnot(None))
        .where(Lead.contact_channel.isnot(None))
        .group_by(Lead.contact_channel)
    )
    lead_stmt = apply_period_channel_market(
        lead_stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    lead_stmt = apply_snapshot_attr(lead_stmt, Lead, filters)
    lead_stmt = _apply_channel(lead_stmt, Lead.contact_channel, filters)
    leads = await session.execute(lead_stmt)
    for channel, count in leads.all():
        items[str(channel)]["leads"] = int(count or 0)

    order_stmt = (
        select(
            Lead.contact_channel,
            Order.currency,
            func.coalesce(func.sum(Order.paid_amount), 0),
            func.count(Order.order_id),
        )
        .select_from(Order)
        .join(Lead, Order.lead_id == Lead.lead_id)
        .where(Order.paid_event_id.isnot(None))
        .where(Lead.contact_channel.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(Lead.contact_channel, Order.currency)
    )
    order_stmt = apply_period_channel_market(
        order_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    order_stmt = apply_snapshot_attr(order_stmt, Order, filters)
    order_stmt = apply_payment_method(order_stmt, Order.payment_method, filters)
    order_stmt = apply_currency(order_stmt, Order.currency, filters)
    order_stmt = _apply_channel(order_stmt, Lead.contact_channel, filters)
    order_rows = await session.execute(order_stmt)
    for channel, currency, total, count in order_rows.all():
        items[str(channel)]["orders_paid"] += int(count or 0)
        add_to_money(
            items[str(channel)]["money"],
            currency,
            gross=total,
            paid_count=count,
        )

    sale_stmt = (
        select(
            Lead.contact_channel,
            ManualSale.currency,
            func.coalesce(func.sum(ManualSale.amount), 0),
            func.count(ManualSale.manual_sale_id),
        )
        .select_from(ManualSale)
        .join(Lead, ManualSale.lead_id == Lead.lead_id)
        .where(ManualSale.event_id.isnot(None))
        .where(ManualSale.cancelled_at.is_(None))
        .where(Lead.contact_channel.isnot(None))
        .where(ManualSale.currency.isnot(None))
        .group_by(Lead.contact_channel, ManualSale.currency)
    )
    sale_stmt = apply_period_channel_market(
        sale_stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    sale_stmt = apply_snapshot_attr(sale_stmt, ManualSale, filters)
    sale_stmt = apply_currency(sale_stmt, ManualSale.currency, filters)
    sale_stmt = _apply_channel(sale_stmt, Lead.contact_channel, filters)
    sale_rows = await session.execute(sale_stmt)
    for channel, currency, total, count in sale_rows.all():
        items[str(channel)]["manual_sales"] += int(count or 0)
        add_to_money(
            items[str(channel)]["money"],
            currency,
            gross=total,
            paid_count=count,
        )

    converting_stmt = (
        select(Lead.contact_channel, func.count())
        .select_from(Lead)
        .where(Lead.event_id.isnot(None))
        .where(Lead.contact_channel.isnot(None))
        .where(
            or_(
                _paid_order_exists(filters),
                _confirmed_manual_sale_exists(filters),
            )
        )
        .group_by(Lead.contact_channel)
    )
    converting_stmt = apply_period_channel_market(
        converting_stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    converting_stmt = apply_snapshot_attr(converting_stmt, Lead, filters)
    converting_stmt = _apply_channel(converting_stmt, Lead.contact_channel, filters)
    converting_rows = await session.execute(converting_stmt)
    for channel, count in converting_rows.all():
        items[str(channel)]["converting_leads"] = int(count or 0)

    refund_stmt = (
        select(
            Lead.contact_channel,
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .select_from(Refund)
        .join(Order, Refund.order_id == Order.order_id)
        .join(Lead, Order.lead_id == Lead.lead_id)
        .where(Lead.contact_channel.isnot(None))
        .group_by(Lead.contact_channel, Refund.currency)
    )
    refund_stmt = apply_matching_order_currency(refund_stmt)
    refund_stmt = apply_period_channel_market(
        refund_stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
        market_code=Order.market_code,
    )
    refund_stmt = apply_payment_method(refund_stmt, Refund.payment_method, filters)
    refund_stmt = apply_currency(refund_stmt, Refund.currency, filters)
    refund_stmt = apply_snapshot_attr(refund_stmt, Order, filters)
    refund_stmt = _apply_channel(refund_stmt, Lead.contact_channel, filters)
    refund_rows = await session.execute(refund_stmt)
    for channel, currency, total in refund_rows.all():
        add_to_money(items[str(channel)]["money"], currency, refunds=total)

    rows = []
    for channel in sorted(items):
        data = items[channel]
        rows.append(
            ContactChannelRow(
                channel=channel,
                intents=data["intents"],
                contacts=data["contacts"],
                leads=data["leads"],
                orders_paid=data["orders_paid"],
                manual_sales=data["manual_sales"],
                money=money_breakdowns(data["money"]),
                contact_to_lead=format_rate(
                    data["leads_from_contacts"],
                    data["contacts"],
                ),
                lead_to_paid_sale=format_rate(
                    data["converting_leads"],
                    data["leads"],
                ),
            )
        )
    return ContactChannelsResponse(items=rows)
