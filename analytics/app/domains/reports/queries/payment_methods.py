from collections import defaultdict

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Order
from domains.projections.models.facts import PaymentMethodEvent, Refund
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_currency,
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
from domains.reports.schemas import PaymentMethodRow, PaymentMethodsResponse


def _empty_method() -> dict:
    return {
        "shown": 0,
        "selected": 0,
        "failed": 0,
        "orders_created": 0,
        "orders_paid": 0,
        "money": empty_money_buckets(),
    }


def _apply_method_filter(stmt, column, filters: ReportFilters):
    if filters.payment_method is None:
        return stmt
    return stmt.where(column == filters.payment_method)


# считает shown/selected/failed по каждому способу оплаты и rate = selected/shown
async def query_payment_methods(
    session: AsyncSession,
    filters: ReportFilters,
) -> PaymentMethodsResponse:
    items: dict[str, dict] = defaultdict(_empty_method)
    shown = func.count(case((PaymentMethodEvent.kind == "shown", 1)))
    selected = func.count(case((PaymentMethodEvent.kind == "selected", 1)))
    failed = func.count(case((PaymentMethodEvent.kind == "failed", 1)))
    event_stmt = (
        select(
            PaymentMethodEvent.payment_method,
            shown,
            selected,
            failed,
        )
        .select_from(PaymentMethodEvent)
        .group_by(PaymentMethodEvent.payment_method)
    )
    event_stmt = apply_period_channel_market(
        event_stmt,
        filters,
        occurred_at=PaymentMethodEvent.occurred_at,
        sales_channel_id=PaymentMethodEvent.sales_channel_id,
    )
    event_stmt = apply_visitor_attr(
        event_stmt,
        filters,
        visitor_id_col=PaymentMethodEvent.visitor_id,
    )
    event_stmt = _apply_method_filter(
        event_stmt,
        PaymentMethodEvent.payment_method,
        filters,
    )
    events = await session.execute(event_stmt)
    for method, shown_count, selected_count, failed_count in events.all():
        row = items[str(method)]
        row["shown"] = int(shown_count)
        row["selected"] = int(selected_count)
        row["failed"] = int(failed_count)

    created_stmt = (
        select(Order.payment_method, func.count(Order.order_id))
        .where(Order.created_event_id.isnot(None))
        .where(Order.payment_method.isnot(None))
        .group_by(Order.payment_method)
    )
    created_stmt = apply_period_channel_market(
        created_stmt,
        filters,
        occurred_at=Order.created_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    created_stmt = apply_snapshot_attr(created_stmt, Order, filters)
    created_stmt = _apply_method_filter(created_stmt, Order.payment_method, filters)
    created_rows = await session.execute(created_stmt)
    for method, count in created_rows.all():
        items[str(method)]["orders_created"] = int(count or 0)

    paid_stmt = (
        select(
            Order.payment_method,
            Order.currency,
            func.coalesce(func.sum(Order.paid_amount), 0),
            func.count(Order.order_id),
        )
        .where(Order.paid_event_id.isnot(None))
        .where(Order.payment_method.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(Order.payment_method, Order.currency)
    )
    paid_stmt = apply_period_channel_market(
        paid_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    paid_stmt = apply_snapshot_attr(paid_stmt, Order, filters)
    paid_stmt = apply_currency(paid_stmt, Order.currency, filters)
    paid_stmt = _apply_method_filter(paid_stmt, Order.payment_method, filters)
    paid_rows = await session.execute(paid_stmt)
    for method, currency, total, count in paid_rows.all():
        items[str(method)]["orders_paid"] += int(count or 0)
        add_to_money(
            items[str(method)]["money"],
            currency,
            gross=total,
            paid_count=count,
        )

    refund_stmt = (
        select(
            Refund.payment_method,
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .where(Refund.payment_method.isnot(None))
        .group_by(Refund.payment_method, Refund.currency)
    )
    refund_stmt = apply_period_channel_market(
        refund_stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
    )
    refund_stmt = apply_currency(refund_stmt, Refund.currency, filters)
    refund_stmt = _apply_method_filter(refund_stmt, Refund.payment_method, filters)
    if filters.source is not None or filters.campaign is not None:
        refund_stmt = refund_stmt.join(Order, Refund.order_id == Order.order_id)
        refund_stmt = apply_snapshot_attr(refund_stmt, Order, filters)
    refund_rows = await session.execute(refund_stmt)
    for method, currency, total in refund_rows.all():
        add_to_money(items[str(method)]["money"], currency, refunds=total)

    rows = []
    for method in sorted(items):
        data = items[method]
        rows.append(
            PaymentMethodRow(
                payment_method=method,
                shown=data["shown"],
                selected=data["selected"],
                failed=data["failed"],
                selected_rate=format_rate(data["selected"], data["shown"]),
                orders_created=data["orders_created"],
                orders_paid=data["orders_paid"],
                selected_to_paid=format_rate(data["orders_paid"], data["selected"]),
                money=money_breakdowns(data["money"]),
            )
        )
    return PaymentMethodsResponse(items=rows)
