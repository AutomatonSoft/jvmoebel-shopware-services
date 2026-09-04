from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Lead, ManualSale, Order, Session, Visitor
from domains.projections.models.facts import Refund
from domains.reports.filters import ReportFilters, attr_column, in_period
from domains.reports.metrics import (
    apply_currency,
    apply_payment_method,
    apply_period_channel_market,
)
from domains.reports.money_agg import ZERO, money_to_api
from domains.reports.schemas import MoneyBreakdown, SourceRow, SourcesResponse


def _source_expr(entity, filters: ReportFilters, *, snapshot: bool):
    return func.coalesce(
        attr_column(entity, filters, "source", snapshot=snapshot),
        "direct",
    )


def _empty_source() -> dict:
    return {
        "visitors": 0,
        "sessions": 0,
        "leads": 0,
        "orders_paid": 0,
        "money": defaultdict(
            lambda: {"gross": ZERO, "refunds": ZERO, "paid_count": 0}
        ),
    }


async def _count_by_source(session: AsyncSession, stmt) -> dict[str, int]:
    result = await session.execute(stmt)
    return {str(source): int(count or 0) for source, count in result.all()}


def _money_rows(bucket: dict) -> list[MoneyBreakdown]:
    rows: list[MoneyBreakdown] = []
    for currency in sorted(bucket):
        values = bucket[currency]
        gross = Decimal(values["gross"])
        refunds = Decimal(values["refunds"])
        paid_count = int(values["paid_count"])
        net = gross - refunds
        aov = ZERO if paid_count == 0 else gross / Decimal(paid_count)
        rows.append(
            MoneyBreakdown(
                currency=currency,
                gross=money_to_api(gross),
                refunds=money_to_api(refunds),
                net=money_to_api(net),
                aov=money_to_api(aov),
            )
        )
    return rows


async def query_sources(
    session: AsyncSession,
    filters: ReportFilters,
) -> SourcesResponse:
    items: dict[str, dict] = defaultdict(_empty_source)
    visitor_source = _source_expr(Visitor, filters, snapshot=False)

    visitor_stmt = (
        select(visitor_source, func.count())
        .select_from(Visitor)
        .where(Visitor.is_stub.is_(False))
        .where(in_period(Visitor.first_seen_at, filters))
        .group_by(visitor_source)
    )
    if filters.sales_channel is not None:
        visitor_stmt = visitor_stmt.where(
            attr_column(Visitor, filters, "sales_channel_id", snapshot=False)
            == filters.sales_channel
        )
    if filters.source is not None:
        visitor_stmt = visitor_stmt.where(visitor_source == filters.source)
    if filters.campaign is not None:
        visitor_stmt = visitor_stmt.where(
            attr_column(Visitor, filters, "campaign", snapshot=False)
            == filters.campaign
        )
    for source, count in (await _count_by_source(session, visitor_stmt)).items():
        items[source]["visitors"] = count

    session_stmt = (
        select(visitor_source, func.count())
        .select_from(Session)
        .join(Visitor, Session.visitor_id == Visitor.visitor_id)
        .where(Session.event_id.isnot(None))
        .group_by(visitor_source)
    )
    session_stmt = apply_period_channel_market(
        session_stmt,
        filters,
        occurred_at=Session.occurred_at,
        sales_channel_id=Session.sales_channel_id,
        market_code=Session.market_code,
    )
    if filters.source is not None:
        session_stmt = session_stmt.where(visitor_source == filters.source)
    if filters.campaign is not None:
        session_stmt = session_stmt.where(
            attr_column(Visitor, filters, "campaign", snapshot=False)
            == filters.campaign
        )
    for source, count in (await _count_by_source(session, session_stmt)).items():
        items[source]["sessions"] = count

    lead_source = _source_expr(Lead, filters, snapshot=True)
    lead_stmt = (
        select(lead_source, func.count())
        .select_from(Lead)
        .where(Lead.event_id.isnot(None))
        .group_by(lead_source)
    )
    lead_stmt = apply_period_channel_market(
        lead_stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    if filters.source is not None:
        lead_stmt = lead_stmt.where(lead_source == filters.source)
    if filters.campaign is not None:
        lead_stmt = lead_stmt.where(
            attr_column(Lead, filters, "campaign", snapshot=True)
            == filters.campaign
        )
    for source, count in (await _count_by_source(session, lead_stmt)).items():
        items[source]["leads"] = count

    order_source = _source_expr(Order, filters, snapshot=True)
    order_stmt = (
        select(
            order_source,
            Order.currency,
            func.coalesce(func.sum(Order.paid_amount), 0),
            func.count(Order.order_id),
        )
        .where(Order.paid_event_id.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(order_source, Order.currency)
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
    if filters.source is not None:
        order_stmt = order_stmt.where(order_source == filters.source)
    if filters.campaign is not None:
        order_stmt = order_stmt.where(
            attr_column(Order, filters, "campaign", snapshot=True)
            == filters.campaign
        )
    order_rows = await session.execute(order_stmt)
    for source, currency, total, count in order_rows.all():
        source_key = str(source)
        items[source_key]["orders_paid"] += int(count or 0)
        money = items[source_key]["money"][str(currency)]
        money["gross"] += Decimal(total or 0)
        money["paid_count"] += int(count or 0)

    sale_source = _source_expr(ManualSale, filters, snapshot=True)
    sale_stmt = (
        select(
            sale_source,
            ManualSale.currency,
            func.coalesce(func.sum(ManualSale.amount), 0),
            func.count(ManualSale.manual_sale_id),
        )
        .where(ManualSale.event_id.isnot(None))
        .where(ManualSale.cancelled_at.is_(None))
        .where(ManualSale.currency.isnot(None))
        .group_by(sale_source, ManualSale.currency)
    )
    sale_stmt = apply_period_channel_market(
        sale_stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    sale_stmt = apply_currency(sale_stmt, ManualSale.currency, filters)
    if filters.source is not None:
        sale_stmt = sale_stmt.where(sale_source == filters.source)
    sale_rows = await session.execute(sale_stmt)
    for source, currency, total, count in sale_rows.all():
        money = items[str(source)]["money"][str(currency)]
        money["gross"] += Decimal(total or 0)
        money["paid_count"] += int(count or 0)

    refund_stmt = (
        select(
            order_source,
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .select_from(Refund)
        .join(Order, Refund.order_id == Order.order_id)
        .group_by(order_source, Refund.currency)
    )
    refund_stmt = apply_period_channel_market(
        refund_stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
    )
    refund_stmt = apply_payment_method(refund_stmt, Refund.payment_method, filters)
    refund_stmt = apply_currency(refund_stmt, Refund.currency, filters)
    if filters.source is not None:
        refund_stmt = refund_stmt.where(order_source == filters.source)
    refund_rows = await session.execute(refund_stmt)
    for source, currency, total in refund_rows.all():
        items[str(source)]["money"][str(currency)]["refunds"] += Decimal(total or 0)

    rows = [
        SourceRow(
            source=source,
            visitors=data["visitors"],
            sessions=data["sessions"],
            leads=data["leads"],
            orders_paid=data["orders_paid"],
            money=_money_rows(data["money"]),
        )
        for source, data in sorted(items.items())
    ]
    return SourcesResponse(items=rows)
