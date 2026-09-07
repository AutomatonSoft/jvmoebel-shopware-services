from collections import defaultdict

from sqlalchemy import func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import (
    Lead,
    ManualSale,
    Order,
    Session,
    Visitor,
)
from domains.projections.models.facts import Contact, Refund
from domains.reports.filters import ReportFilters, attr_column, in_period
from domains.reports.metrics import (
    apply_currency,
    apply_payment_method,
    apply_period_channel_market,
    apply_snapshot_attr,
    duration_seconds,
    format_avg_seconds,
    format_rate,
)
from domains.reports.money_agg import (
    add_to_money,
    empty_money_buckets,
    money_breakdowns,
)
from domains.reports.schemas import SourceRow, SourcesResponse


def _source_expr(entity, filters: ReportFilters, *, snapshot: bool):
    return func.coalesce(
        attr_column(entity, filters, "source", snapshot=snapshot),
        "direct",
    )


def _campaign_expr(entity, filters: ReportFilters, *, snapshot: bool):
    return attr_column(entity, filters, "campaign", snapshot=snapshot)


def _empty_source() -> dict:
    return {
        "visitors": 0,
        "sessions": 0,
        "contacts": 0,
        "leads": 0,
        "orders_created": 0,
        "orders_paid": 0,
        "manual_sales": 0,
        "money": empty_money_buckets(),
        "first_visit_to_lead_seconds": None,
        "first_visit_to_paid_sale_seconds": None,
    }


def _row_key(source, campaign) -> tuple[str, str | None]:
    campaign_key = None if campaign is None else str(campaign)
    return (str(source), campaign_key)


def _apply_source_campaign(stmt, source_expr, campaign_expr, filters: ReportFilters):
    if filters.source is not None:
        stmt = stmt.where(source_expr == filters.source)
    if filters.campaign is not None:
        stmt = stmt.where(campaign_expr == filters.campaign)
    return stmt


async def _count_by_key(
    session: AsyncSession, stmt
) -> dict[tuple[str, str | None], int]:
    result = await session.execute(stmt)
    return {
        _row_key(source, campaign): int(count or 0)
        for source, campaign, count in result.all()
    }


async def query_sources(
    session: AsyncSession,
    filters: ReportFilters,
) -> SourcesResponse:
    items: dict[tuple[str, str | None], dict] = defaultdict(_empty_source)
    visitor_source = _source_expr(Visitor, filters, snapshot=False)
    visitor_campaign = _campaign_expr(Visitor, filters, snapshot=False)

    visitor_stmt = (
        select(visitor_source, visitor_campaign, func.count())
        .select_from(Visitor)
        .where(Visitor.is_stub.is_(False))
        .where(in_period(Visitor.first_seen_at, filters))
        .group_by(visitor_source, visitor_campaign)
    )
    if filters.sales_channel is not None:
        visitor_stmt = visitor_stmt.where(
            attr_column(Visitor, filters, "sales_channel_id", snapshot=False)
            == filters.sales_channel
        )
    visitor_stmt = _apply_source_campaign(
        visitor_stmt,
        visitor_source,
        visitor_campaign,
        filters,
    )
    for key, count in (await _count_by_key(session, visitor_stmt)).items():
        items[key]["visitors"] = count

    session_stmt = (
        select(visitor_source, visitor_campaign, func.count())
        .select_from(Session)
        .join(Visitor, Session.visitor_id == Visitor.visitor_id)
        .where(Session.event_id.isnot(None))
        .group_by(visitor_source, visitor_campaign)
    )
    session_stmt = apply_period_channel_market(
        session_stmt,
        filters,
        occurred_at=Session.occurred_at,
        sales_channel_id=Session.sales_channel_id,
        market_code=Session.market_code,
    )
    session_stmt = _apply_source_campaign(
        session_stmt,
        visitor_source,
        visitor_campaign,
        filters,
    )
    for key, count in (await _count_by_key(session, session_stmt)).items():
        items[key]["sessions"] = count

    lead_source = _source_expr(Lead, filters, snapshot=True)
    lead_campaign = _campaign_expr(Lead, filters, snapshot=True)
    lead_stmt = (
        select(lead_source, lead_campaign, func.count())
        .select_from(Lead)
        .where(Lead.event_id.isnot(None))
        .group_by(lead_source, lead_campaign)
    )
    lead_stmt = apply_period_channel_market(
        lead_stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    lead_stmt = _apply_source_campaign(
        lead_stmt,
        lead_source,
        lead_campaign,
        filters,
    )
    for key, count in (await _count_by_key(session, lead_stmt)).items():
        items[key]["leads"] = count

    contact_stmt = (
        select(lead_source, lead_campaign, func.count())
        .select_from(Contact)
        .join(Lead, Contact.lead_id == Lead.lead_id)
        .group_by(lead_source, lead_campaign)
    )
    contact_stmt = apply_period_channel_market(
        contact_stmt,
        filters,
        occurred_at=Contact.occurred_at,
        sales_channel_id=Contact.sales_channel_id,
        market_code=Contact.market_code,
    )
    contact_stmt = apply_snapshot_attr(contact_stmt, Lead, filters)
    for key, count in (await _count_by_key(session, contact_stmt)).items():
        items[key]["contacts"] = count

    order_source = _source_expr(Order, filters, snapshot=True)
    order_campaign = _campaign_expr(Order, filters, snapshot=True)
    created_stmt = (
        select(order_source, order_campaign, func.count(Order.order_id))
        .where(Order.created_event_id.isnot(None))
        .group_by(order_source, order_campaign)
    )
    created_stmt = apply_period_channel_market(
        created_stmt,
        filters,
        occurred_at=Order.created_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    created_stmt = apply_payment_method(created_stmt, Order.payment_method, filters)
    created_stmt = _apply_source_campaign(
        created_stmt,
        order_source,
        order_campaign,
        filters,
    )
    for key, count in (await _count_by_key(session, created_stmt)).items():
        items[key]["orders_created"] = count

    order_stmt = (
        select(
            order_source,
            order_campaign,
            Order.currency,
            func.coalesce(func.sum(Order.paid_amount), 0),
            func.count(Order.order_id),
        )
        .where(Order.paid_event_id.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(order_source, order_campaign, Order.currency)
    )
    order_stmt = apply_period_channel_market(
        order_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    order_stmt = apply_payment_method(order_stmt, Order.payment_method, filters)
    order_stmt = apply_currency(order_stmt, Order.currency, filters)
    order_stmt = _apply_source_campaign(
        order_stmt,
        order_source,
        order_campaign,
        filters,
    )
    order_rows = await session.execute(order_stmt)
    for source, campaign, currency, total, count in order_rows.all():
        key = _row_key(source, campaign)
        items[key]["orders_paid"] += int(count or 0)
        add_to_money(
            items[key]["money"],
            currency,
            gross=total,
            paid_count=count,
        )

    sale_source = _source_expr(ManualSale, filters, snapshot=True)
    sale_campaign = _campaign_expr(ManualSale, filters, snapshot=True)
    sale_stmt = (
        select(
            sale_source,
            sale_campaign,
            ManualSale.currency,
            func.coalesce(func.sum(ManualSale.amount), 0),
            func.count(ManualSale.manual_sale_id),
        )
        .where(ManualSale.event_id.isnot(None))
        .where(ManualSale.cancelled_at.is_(None))
        .where(ManualSale.currency.isnot(None))
        .group_by(sale_source, sale_campaign, ManualSale.currency)
    )
    sale_stmt = apply_period_channel_market(
        sale_stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    sale_stmt = apply_currency(sale_stmt, ManualSale.currency, filters)
    sale_stmt = _apply_source_campaign(
        sale_stmt,
        sale_source,
        sale_campaign,
        filters,
    )
    sale_rows = await session.execute(sale_stmt)
    for source, campaign, currency, total, count in sale_rows.all():
        key = _row_key(source, campaign)
        items[key]["manual_sales"] += int(count or 0)
        add_to_money(
            items[key]["money"],
            currency,
            gross=total,
            paid_count=count,
        )

    refund_stmt = (
        select(
            order_source,
            order_campaign,
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .select_from(Refund)
        .join(Order, Refund.order_id == Order.order_id)
        .group_by(order_source, order_campaign, Refund.currency)
    )
    refund_stmt = apply_period_channel_market(
        refund_stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
    )
    refund_stmt = apply_payment_method(refund_stmt, Refund.payment_method, filters)
    refund_stmt = apply_currency(refund_stmt, Refund.currency, filters)
    refund_stmt = _apply_source_campaign(
        refund_stmt,
        order_source,
        order_campaign,
        filters,
    )
    refund_rows = await session.execute(refund_stmt)
    for source, campaign, currency, total in refund_rows.all():
        add_to_money(
            items[_row_key(source, campaign)]["money"],
            currency,
            refunds=total,
        )

    lead_time_stmt = (
        select(
            lead_source,
            lead_campaign,
            func.avg(duration_seconds(Lead.created_at, Visitor.first_seen_at)),
        )
        .select_from(Lead)
        .join(Visitor, Lead.visitor_id == Visitor.visitor_id)
        .where(
            Lead.event_id.isnot(None),
            Visitor.first_seen_at.isnot(None),
            Lead.created_at >= Visitor.first_seen_at,
        )
        .group_by(lead_source, lead_campaign)
    )
    lead_time_stmt = apply_period_channel_market(
        lead_time_stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    lead_time_stmt = _apply_source_campaign(
        lead_time_stmt,
        lead_source,
        lead_campaign,
        filters,
    )
    lead_times = await session.execute(lead_time_stmt)
    for source, campaign, value in lead_times.all():
        items[_row_key(source, campaign)]["first_visit_to_lead_seconds"] = (
            format_avg_seconds(value)
        )

    order_time_stmt = (
        select(
            order_source.label("source"),
            order_campaign.label("campaign"),
            duration_seconds(Order.paid_at, Visitor.first_seen_at).label("seconds"),
        )
        .select_from(Order)
        .join(Visitor, Order.visitor_id == Visitor.visitor_id)
        .where(
            Order.paid_event_id.isnot(None),
            Visitor.first_seen_at.isnot(None),
            Order.paid_at >= Visitor.first_seen_at,
        )
    )
    order_time_stmt = apply_period_channel_market(
        order_time_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    order_time_stmt = apply_payment_method(
        order_time_stmt, Order.payment_method, filters
    )
    order_time_stmt = apply_currency(order_time_stmt, Order.currency, filters)
    order_time_stmt = _apply_source_campaign(
        order_time_stmt,
        order_source,
        order_campaign,
        filters,
    )

    sale_time_stmt = (
        select(
            sale_source.label("source"),
            sale_campaign.label("campaign"),
            duration_seconds(ManualSale.confirmed_at, Visitor.first_seen_at).label(
                "seconds"
            ),
        )
        .select_from(ManualSale)
        .join(Visitor, ManualSale.visitor_id == Visitor.visitor_id)
        .where(
            ManualSale.event_id.isnot(None),
            ManualSale.cancelled_at.is_(None),
            Visitor.first_seen_at.isnot(None),
            ManualSale.confirmed_at >= Visitor.first_seen_at,
        )
    )
    sale_time_stmt = apply_period_channel_market(
        sale_time_stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    sale_time_stmt = apply_currency(sale_time_stmt, ManualSale.currency, filters)
    sale_time_stmt = _apply_source_campaign(
        sale_time_stmt,
        sale_source,
        sale_campaign,
        filters,
    )
    durations = union_all(order_time_stmt, sale_time_stmt).subquery()
    paid_time_stmt = select(
        durations.c.source,
        durations.c.campaign,
        func.avg(durations.c.seconds),
    ).group_by(durations.c.source, durations.c.campaign)
    paid_times = await session.execute(paid_time_stmt)
    for source, campaign, value in paid_times.all():
        items[_row_key(source, campaign)]["first_visit_to_paid_sale_seconds"] = (
            format_avg_seconds(value)
        )

    rows = []
    for source, campaign in sorted(
        items,
        key=lambda key: (key[0], key[1] or ""),
    ):
        data = items[(source, campaign)]
        paid_sales = data["orders_paid"] + data["manual_sales"]
        rows.append(
            SourceRow(
                source=source,
                campaign=campaign,
                visitors=data["visitors"],
                sessions=data["sessions"],
                contacts=data["contacts"],
                leads=data["leads"],
                orders_created=data["orders_created"],
                orders_paid=data["orders_paid"],
                manual_sales=data["manual_sales"],
                money=money_breakdowns(data["money"]),
                session_to_lead=format_rate(data["leads"], data["sessions"]),
                session_to_paid_sale=format_rate(paid_sales, data["sessions"]),
                lead_to_paid_sale=format_rate(paid_sales, data["leads"]),
                first_visit_to_lead_seconds=data["first_visit_to_lead_seconds"],
                first_visit_to_paid_sale_seconds=data[
                    "first_visit_to_paid_sale_seconds"
                ],
            )
        )
    return SourcesResponse(items=rows)
