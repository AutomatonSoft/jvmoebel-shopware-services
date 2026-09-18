from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import ManualSale, Order
from domains.projections.models.facts import Refund
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_currency,
    apply_matching_order_currency,
    apply_payment_method,
    apply_period_channel_market,
    apply_snapshot_attr,
)
from domains.reports.money_agg import (
    add_to_money,
    empty_money_buckets,
    money_breakdowns,
)
from domains.reports.schemas import DailyPoint, OverviewDailyResponse


def _day_range(filters: ReportFilters) -> list[date]:
    start = filters.period_from.date()
    end = filters.period_to.date()
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def _as_day(value: object) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).date()
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"Unsupported day value: {value!r}")


async def query_overview_daily(
    session: AsyncSession,
    filters: ReportFilters,
) -> OverviewDailyResponse:
    buckets: dict[date, dict] = {
        day: {
            "orders_paid": 0,
            "manual_sales": 0,
            "money": empty_money_buckets(),
        }
        for day in _day_range(filters)
    }

    day_expr = func.date_trunc("day", func.timezone("UTC", Order.paid_at))
    order_stmt = (
        select(
            day_expr.label("day"),
            Order.currency,
            func.count(Order.order_id),
            func.coalesce(func.sum(Order.paid_amount), 0),
        )
        .where(Order.paid_event_id.isnot(None))
        .where(Order.paid_at.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(day_expr, Order.currency)
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
    for day_value, currency, count, total in (await session.execute(order_stmt)).all():
        day = _as_day(day_value)
        if day not in buckets:
            continue
        buckets[day]["orders_paid"] += int(count or 0)
        add_to_money(
            buckets[day]["money"],
            currency,
            gross=Decimal(total or 0),
            paid_count=int(count or 0),
        )

    sale_day = func.date_trunc(
        "day",
        func.timezone("UTC", ManualSale.confirmed_at),
    )
    sale_stmt = (
        select(
            sale_day.label("day"),
            ManualSale.currency,
            func.count(ManualSale.manual_sale_id),
            func.coalesce(func.sum(ManualSale.amount), 0),
        )
        .where(ManualSale.event_id.isnot(None))
        .where(ManualSale.cancelled_at.is_(None))
        .where(ManualSale.confirmed_at.isnot(None))
        .where(ManualSale.currency.isnot(None))
        .group_by(sale_day, ManualSale.currency)
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
    for day_value, currency, count, total in (await session.execute(sale_stmt)).all():
        day = _as_day(day_value)
        if day not in buckets:
            continue
        buckets[day]["manual_sales"] += int(count or 0)
        add_to_money(
            buckets[day]["money"],
            currency,
            gross=Decimal(total or 0),
            paid_count=int(count or 0),
        )

    refund_day = func.date_trunc(
        "day",
        func.timezone("UTC", Refund.refunded_at),
    )
    refund_stmt = (
        select(
            refund_day.label("day"),
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .select_from(Refund)
        .join(Order, Refund.order_id == Order.order_id)
        .where(Refund.currency.isnot(None))
        .group_by(refund_day, Refund.currency)
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
    for day_value, currency, total in (await session.execute(refund_stmt)).all():
        day = _as_day(day_value)
        if day not in buckets:
            continue
        add_to_money(
            buckets[day]["money"],
            currency,
            refunds=Decimal(total or 0),
        )

    items = [
        DailyPoint(
            date=day,
            orders_paid=int(bucket["orders_paid"]),
            manual_sales=int(bucket["manual_sales"]),
            paid_sales=int(bucket["orders_paid"]) + int(bucket["manual_sales"]),
            money=money_breakdowns(bucket["money"]),
        )
        for day, bucket in buckets.items()
    ]
    return OverviewDailyResponse(items=items)
