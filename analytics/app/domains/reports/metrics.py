from decimal import Decimal

from sqlalchemy import Select, exists, func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import (
    Lead,
    ManualSale,
    Order,
    Session,
    Visitor,
)
from domains.projections.models.facts import (
    CartAdd,
    Checkout,
    Contact,
    ContactIntent,
    ProductView,
)
from domains.reports.filters import ReportFilters, attr_column, in_period

RATE_QUANT = Decimal("0.0001")


async def scalar_int(session: AsyncSession, stmt: Select) -> int:
    value = await session.scalar(stmt)
    return int(value or 0)


def format_rate(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return format(
        (Decimal(numerator) / Decimal(denominator)).quantize(RATE_QUANT),
        "f",
    )


def format_change_pct(current: Decimal, previous: Decimal) -> str | None:
    if previous == 0:
        return None
    return format(
        ((current - previous) / previous).quantize(RATE_QUANT),
        "f",
    )


def format_avg_seconds(value: Decimal | float | None) -> str | None:
    if value is None:
        return None
    return format(Decimal(value).quantize(Decimal("1")), "f")


def apply_period_channel_market(
    stmt: Select,
    filters: ReportFilters,
    *,
    occurred_at,
    sales_channel_id=None,
    market_code=None,
) -> Select:
    stmt = stmt.where(in_period(occurred_at, filters))
    if filters.sales_channel is not None and sales_channel_id is not None:
        stmt = stmt.where(sales_channel_id == filters.sales_channel)
    if filters.market is not None and market_code is not None:
        stmt = stmt.where(market_code == filters.market)
    return stmt


def apply_visitor_attr(
    stmt: Select,
    filters: ReportFilters,
    *,
    visitor_joined: bool = False,
    visitor_id_col=None,
) -> Select:
    needs_attr = filters.source is not None or filters.campaign is not None
    if not needs_attr:
        return stmt
    if not visitor_joined:
        # Iner join запроса и таблицы Visitors, по строкам где значение в колонке,
        # переданной в visitor_id_col (id посетителя) в запросе равно id в таблице посетителей
        stmt = stmt.join(Visitor, visitor_id_col == Visitor.visitor_id)
    if filters.source is not None:
        stmt = stmt.where(
            attr_column(Visitor, filters, "source", snapshot=False) == filters.source
        )
    if filters.campaign is not None:
        stmt = stmt.where(
            attr_column(Visitor, filters, "campaign", snapshot=False)
            == filters.campaign
        )
    return stmt


def apply_snapshot_attr(stmt: Select, entity, filters: ReportFilters) -> Select:
    if filters.source is not None:
        stmt = stmt.where(
            attr_column(entity, filters, "source", snapshot=True) == filters.source
        )
    if filters.campaign is not None:
        stmt = stmt.where(
            attr_column(entity, filters, "campaign", snapshot=True) == filters.campaign
        )
    return stmt


def apply_currency(stmt: Select, column, filters: ReportFilters) -> Select:
    if filters.currency is None:
        return stmt
    return stmt.where(column == filters.currency)


def apply_payment_method(stmt: Select, column, filters: ReportFilters) -> Select:
    if filters.payment_method is None:
        return stmt
    return stmt.where(column == filters.payment_method)


def apply_sku(stmt: Select, column, filters: ReportFilters) -> Select:
    if filters.sku is None:
        return stmt
    return stmt.where(column == filters.sku)


async def count_visitors(session: AsyncSession, filters: ReportFilters) -> int:
    stmt = (
        select(func.count())
        .select_from(Visitor)
        .where(
            Visitor.is_stub.is_(False),
            in_period(Visitor.first_seen_at, filters),
        )
    )
    if filters.sales_channel is not None:
        stmt = stmt.where(
            attr_column(Visitor, filters, "sales_channel_id", snapshot=False)
            == filters.sales_channel
        )
    if filters.source is not None:
        stmt = stmt.where(
            attr_column(Visitor, filters, "source", snapshot=False) == filters.source
        )
    if filters.campaign is not None:
        stmt = stmt.where(
            attr_column(Visitor, filters, "campaign", snapshot=False)
            == filters.campaign
        )
    if filters.market is not None:
        # Оставляем только те строки запроса, для которых у visitor есть хотя бы одна подходящая session
        stmt = stmt.where(
            exists().where(
                Session.visitor_id == Visitor.visitor_id,
                Session.event_id.isnot(None),
                Session.market_code == filters.market,
            )
        )
    return await scalar_int(session, stmt)


async def count_sessions(session: AsyncSession, filters: ReportFilters) -> int:
    stmt = (
        select(func.count())
        .select_from(Session)
        .where(
            Session.event_id.isnot(None),
        )
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Session.occurred_at,
        sales_channel_id=Session.sales_channel_id,
        market_code=Session.market_code,
    )
    stmt = apply_visitor_attr(
        stmt,
        filters,
        visitor_id_col=Session.visitor_id,
    )
    return await scalar_int(session, stmt)


async def count_leads(session: AsyncSession, filters: ReportFilters) -> int:
    stmt = (
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.event_id.isnot(None),
        )
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    stmt = apply_snapshot_attr(stmt, Lead, filters)
    return await scalar_int(session, stmt)


async def count_orders_created(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Order)
        .where(
            Order.created_event_id.isnot(None),
        )
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Order.created_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    stmt = apply_snapshot_attr(stmt, Order, filters)
    stmt = apply_payment_method(stmt, Order.payment_method, filters)
    return await scalar_int(session, stmt)


async def count_orders_paid(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Order)
        .where(
            Order.paid_event_id.isnot(None),
        )
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
    return await scalar_int(session, stmt)


async def count_fact_visitors(
    session: AsyncSession,
    filters: ReportFilters,
    *,
    model,
    visitor_id_col,
    occurred_at,
    sales_channel_id,
    sku_col=None,
    channel_col=None,
) -> int:
    stmt = (
        select(func.count(func.distinct(visitor_id_col)))
        .select_from(model)
        # Оставляем только те строки факта, чей visitor живой, не заглушка
        .join(Visitor, visitor_id_col == Visitor.visitor_id)
        .where(Visitor.is_stub.is_(False))
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=occurred_at,
        sales_channel_id=sales_channel_id,
    )
    stmt = apply_visitor_attr(
        stmt,
        filters,
        visitor_joined=True,
        visitor_id_col=visitor_id_col,
    )
    if sku_col is not None:
        stmt = apply_sku(stmt, sku_col, filters)
    if channel_col is not None and filters.channel is not None:
        stmt = stmt.where(channel_col == filters.channel)
    return await scalar_int(session, stmt)


async def count_product_viewers(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_visitors(
        session,
        filters,
        model=ProductView,
        visitor_id_col=ProductView.visitor_id,
        occurred_at=ProductView.occurred_at,
        sales_channel_id=ProductView.sales_channel_id,
        sku_col=ProductView.sku,
    )


async def count_cart_adders(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_visitors(
        session,
        filters,
        model=CartAdd,
        visitor_id_col=CartAdd.visitor_id,
        occurred_at=CartAdd.occurred_at,
        sales_channel_id=CartAdd.sales_channel_id,
        sku_col=CartAdd.sku,
    )


async def count_checkout_visitors(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_visitors(
        session,
        filters,
        model=Checkout,
        visitor_id_col=Checkout.visitor_id,
        occurred_at=Checkout.occurred_at,
        sales_channel_id=Checkout.sales_channel_id,
    )


async def count_fact_rows(
    session: AsyncSession,
    filters: ReportFilters,
    *,
    model,
    visitor_id_col,
    occurred_at,
    sales_channel_id,
    sku_col=None,
) -> int:
    stmt = select(func.count()).select_from(model)
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=occurred_at,
        sales_channel_id=sales_channel_id,
    )
    stmt = apply_visitor_attr(
        stmt,
        filters,
        visitor_id_col=visitor_id_col,
    )
    if sku_col is not None:
        stmt = apply_sku(stmt, sku_col, filters)
    return await scalar_int(session, stmt)


async def count_product_views(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_rows(
        session,
        filters,
        model=ProductView,
        visitor_id_col=ProductView.visitor_id,
        occurred_at=ProductView.occurred_at,
        sales_channel_id=ProductView.sales_channel_id,
        sku_col=ProductView.sku,
    )


async def count_cart_adds(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_rows(
        session,
        filters,
        model=CartAdd,
        visitor_id_col=CartAdd.visitor_id,
        occurred_at=CartAdd.occurred_at,
        sales_channel_id=CartAdd.sales_channel_id,
        sku_col=CartAdd.sku,
    )


async def count_checkouts(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_rows(
        session,
        filters,
        model=Checkout,
        visitor_id_col=Checkout.visitor_id,
        occurred_at=Checkout.occurred_at,
        sales_channel_id=Checkout.sales_channel_id,
    )


async def count_contact_intent_visitors(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    return await count_fact_visitors(
        session,
        filters,
        model=ContactIntent,
        visitor_id_col=ContactIntent.visitor_id,
        occurred_at=ContactIntent.occurred_at,
        sales_channel_id=ContactIntent.sales_channel_id,
        channel_col=ContactIntent.channel,
    )


async def count_leads_won(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    stmt = (
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.event_id.isnot(None),
            Lead.won_at.isnot(None),
        )
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Lead.won_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    stmt = apply_snapshot_attr(stmt, Lead, filters)
    if filters.channel is not None:
        stmt = stmt.where(Lead.contact_channel == filters.channel)
    return await scalar_int(session, stmt)


async def count_contacts(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    stmt = select(func.count()).select_from(Contact)
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Contact.occurred_at,
        sales_channel_id=Contact.sales_channel_id,
        market_code=Contact.market_code,
    )
    if filters.channel is not None:
        stmt = stmt.where(Contact.contact_channel == filters.channel)
    if filters.source is not None or filters.campaign is not None:
        stmt = stmt.join(Lead, Contact.lead_id == Lead.lead_id)
        stmt = apply_snapshot_attr(stmt, Lead, filters)
    return await scalar_int(session, stmt)


async def count_manual_sales(
    session: AsyncSession,
    filters: ReportFilters,
) -> int:
    stmt = (
        select(func.count())
        .select_from(ManualSale)
        .where(
            ManualSale.event_id.isnot(None),
            ManualSale.cancelled_at.is_(None),
        )
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
    return await scalar_int(session, stmt)


# сколько секунд прошло между двумя временными метками
def duration_seconds(end_at, start_at):
    return func.extract("epoch", end_at - start_at)


async def avg_first_visit_to_lead_seconds(
    session: AsyncSession,
    filters: ReportFilters,
) -> str | None:
    stmt = (
        select(func.avg(duration_seconds(Lead.created_at, Visitor.first_seen_at)))
        .select_from(Lead)
        .join(Visitor, Lead.visitor_id == Visitor.visitor_id)
        .where(
            Lead.event_id.isnot(None),
            Visitor.first_seen_at.isnot(None),
            Lead.created_at >= Visitor.first_seen_at,
        )
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=Lead.created_at,
        sales_channel_id=Lead.sales_channel_id,
        market_code=Lead.market_code,
    )
    stmt = apply_snapshot_attr(stmt, Lead, filters)
    return format_avg_seconds(await session.scalar(stmt))


async def avg_first_visit_to_paid_sale_seconds(
    session: AsyncSession,
    filters: ReportFilters,
) -> str | None:
    order_stmt = (
        select(duration_seconds(Order.paid_at, Visitor.first_seen_at).label("seconds"))
        .select_from(Order)
        .join(Visitor, Order.visitor_id == Visitor.visitor_id)
        .where(
            Order.paid_event_id.isnot(None),
            Visitor.first_seen_at.isnot(None),
            Order.paid_at >= Visitor.first_seen_at,
        )
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

    sale_stmt = (
        select(
            duration_seconds(ManualSale.confirmed_at, Visitor.first_seen_at).label(
                "seconds"
            )
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
    sale_stmt = apply_period_channel_market(
        sale_stmt,
        filters,
        occurred_at=ManualSale.confirmed_at,
        sales_channel_id=ManualSale.sales_channel_id,
        market_code=ManualSale.market_code,
    )
    sale_stmt = apply_snapshot_attr(sale_stmt, ManualSale, filters)
    sale_stmt = apply_currency(sale_stmt, ManualSale.currency, filters)

    durations = union_all(order_stmt, sale_stmt).subquery()
    value = await session.scalar(select(func.avg(durations.c.seconds)))
    return format_avg_seconds(value)
