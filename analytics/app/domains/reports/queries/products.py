from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Order, Visitor
from domains.projections.models.facts import CartAdd, OrderLine, ProductView
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_period_channel_market,
    apply_sku,
    apply_snapshot_attr,
    apply_visitor_attr,
)
from domains.reports.schemas import ProductRow, ProductsResponse


async def query_products(
    session: AsyncSession,
    filters: ReportFilters,
) -> ProductsResponse:
    items: dict[str, dict[str, int]] = defaultdict(
        lambda: {"views": 0, "cart_adds": 0, "paid_quantity": 0}
    )

    views_stmt = (
        select(ProductView.sku, func.count())
        .select_from(ProductView)
        .join(Visitor, ProductView.visitor_id == Visitor.visitor_id)
        .where(Visitor.is_stub.is_(False))
        .group_by(ProductView.sku)
    )
    views_stmt = apply_period_channel_market(
        views_stmt,
        filters,
        occurred_at=ProductView.occurred_at,
        sales_channel_id=ProductView.sales_channel_id,
    )
    views_stmt = apply_visitor_attr(
        views_stmt,
        filters,
        visitor_joined=True,
        visitor_id_col=ProductView.visitor_id,
    )
    views_stmt = apply_sku(views_stmt, ProductView.sku, filters)
    views = await session.execute(views_stmt)
    for sku, count in views.all():
        items[str(sku)]["views"] = int(count or 0)

    cart_stmt = (
        select(CartAdd.sku, func.count())
        .select_from(CartAdd)
        .join(Visitor, CartAdd.visitor_id == Visitor.visitor_id)
        .where(Visitor.is_stub.is_(False))
        .group_by(CartAdd.sku)
    )
    cart_stmt = apply_period_channel_market(
        cart_stmt,
        filters,
        occurred_at=CartAdd.occurred_at,
        sales_channel_id=CartAdd.sales_channel_id,
    )
    cart_stmt = apply_visitor_attr(
        cart_stmt,
        filters,
        visitor_joined=True,
        visitor_id_col=CartAdd.visitor_id,
    )
    cart_stmt = apply_sku(cart_stmt, CartAdd.sku, filters)
    cart_rows = await session.execute(cart_stmt)
    for sku, count in cart_rows.all():
        items[str(sku)]["cart_adds"] = int(count or 0)

    paid_stmt = (
        select(
            OrderLine.product_number,
            func.coalesce(func.sum(OrderLine.quantity), 0),
        )
        .join(Order, OrderLine.order_id == Order.order_id)
        .where(OrderLine.is_paid_snapshot.is_(True))
        .where(OrderLine.product_number.isnot(None))
        .where(Order.paid_event_id.isnot(None))
        .group_by(OrderLine.product_number)
    )
    paid_stmt = apply_period_channel_market(
        paid_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    paid_stmt = apply_snapshot_attr(paid_stmt, Order, filters)
    paid_stmt = apply_sku(paid_stmt, OrderLine.product_number, filters)
    paid_rows = await session.execute(paid_stmt)
    for sku, quantity in paid_rows.all():
        items[str(sku)]["paid_quantity"] = int(quantity or 0)

    rows = [
        ProductRow(
            sku=sku,
            views=data["views"],
            cart_adds=data["cart_adds"],
            paid_quantity=data["paid_quantity"],
        )
        for sku, data in sorted(items.items())
    ]
    return ProductsResponse(items=rows)
