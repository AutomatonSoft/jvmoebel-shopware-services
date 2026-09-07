from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import ManualSale, Order
from domains.projections.models.facts import Refund
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_currency,
    apply_payment_method,
    apply_period_channel_market,
    apply_snapshot_attr,
)
from domains.reports.schemas import MoneyBreakdown

MONEY_QUANT = Decimal("0.0001")
ZERO = Decimal("0")


# округляет до 4 знаков после запятой и форматируем в обычную строку
def money_to_api(value: Decimal) -> str:
    return format(value.quantize(MONEY_QUANT), "f")


def _empty_bucket() -> dict[str, Decimal | int]:
    return {"gross": ZERO, "refunds": ZERO, "paid_count": 0}


def empty_money_buckets() -> dict[str, dict[str, Decimal | int]]:
    return defaultdict(_empty_bucket)


def add_to_money(
    buckets: dict[str, dict[str, Decimal | int]],
    currency: object,
    *,
    gross: Decimal | int | str | None = 0,
    refunds: Decimal | int | str | None = 0,
    paid_count: int | None = 0,
) -> None:
    if currency is None:
        return
    bucket = buckets[str(currency)]
    bucket["gross"] += Decimal(gross or 0)
    bucket["refunds"] += Decimal(refunds or 0)
    bucket["paid_count"] += int(paid_count or 0)


# преобразует словарь с данными о доходах и возвратах в список MoneyBreakdown
def money_breakdowns(
    buckets: dict[str, dict[str, Decimal | int]],
) -> list[MoneyBreakdown]:
    return _to_breakdowns(buckets)


def _to_breakdowns(
    buckets: dict[str, dict[str, Decimal | int]],
) -> list[MoneyBreakdown]:
    rows: list[MoneyBreakdown] = []
    for currency in sorted(buckets):
        bucket = buckets[currency]
        gross = Decimal(bucket["gross"])
        refunds = Decimal(bucket["refunds"])
        paid_count = int(bucket["paid_count"])
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


async def _add_order_gross(
    session: AsyncSession,
    filters: ReportFilters,
    buckets: dict[str, dict[str, Decimal | int]],
) -> None:
    stmt = (
        select(
            Order.currency,
            func.coalesce(func.sum(Order.paid_amount), 0),
            func.count(Order.order_id),
        )
        .where(Order.paid_event_id.isnot(None))
        .where(Order.currency.isnot(None))
        .group_by(Order.currency)
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    stmt = apply_snapshot_attr(stmt, Order, filters)
    stmt = apply_payment_method(stmt, Order.payment_method, filters)
    stmt = apply_currency(stmt, Order.currency, filters)
    result = await session.execute(stmt)
    for currency, total, count in result.all():
        bucket = buckets[str(currency)]
        bucket["gross"] += Decimal(total or 0)
        bucket["paid_count"] += int(count or 0)


# добавляет в корзины суммы живых не отменённых ручных продаж, группируя по валюте
async def _add_manual_sale_gross(
    session: AsyncSession,
    filters: ReportFilters,
    buckets: dict[str, dict[str, Decimal | int]],
) -> None:
    stmt = (
        select(
            ManualSale.currency,
            # COALESCE(x, 0) подменяет NULL на 0
            # Тогда в Python total всегда число, и
            # bucket["gross"] += Decimal(total) не падает на None
            func.coalesce(func.sum(ManualSale.amount), 0),
            func.count(ManualSale.manual_sale_id),
        )
        .where(ManualSale.event_id.isnot(None))
        .where(ManualSale.cancelled_at.is_(None))
        .where(ManualSale.currency.isnot(None))
        .group_by(ManualSale.currency)
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    stmt = apply_snapshot_attr(stmt, ManualSale, filters)
    stmt = apply_currency(stmt, ManualSale.currency, filters)
    result = await session.execute(stmt)
    for currency, total, count in result.all():
        bucket = buckets[str(currency)]
        bucket["gross"] += Decimal(total or 0)
        bucket["paid_count"] += int(count or 0)


async def _add_refunds(
    session: AsyncSession,
    filters: ReportFilters,
    buckets: dict[str, dict[str, Decimal | int]],
) -> None:
    stmt = (
        select(
            Refund.currency,
            func.coalesce(func.sum(Refund.refund_amount), 0),
        )
        .where(Refund.currency.isnot(None))
        .group_by(Refund.currency)
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
    )
    stmt = apply_payment_method(stmt, Refund.payment_method, filters)
    stmt = apply_currency(stmt, Refund.currency, filters)
    if filters.source is not None or filters.campaign is not None:
        stmt = stmt.join(Order, Refund.order_id == Order.order_id)
        stmt = apply_snapshot_attr(stmt, Order, filters)
    result = await session.execute(stmt)
    for currency, total in result.all():
        buckets[str(currency)]["refunds"] += Decimal(total or 0)


async def aggregate_money(
    session: AsyncSession,
    filters: ReportFilters,
) -> list[MoneyBreakdown]:
    buckets = empty_money_buckets()
    await _add_order_gross(session, filters, buckets)
    await _add_manual_sale_gross(session, filters, buckets)
    await _add_refunds(session, filters, buckets)
    return money_breakdowns(buckets)
