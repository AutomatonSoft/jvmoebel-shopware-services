from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Order, Visitor
from domains.projections.models.facts import CartAdd, OrderLine, ProductView, Refund, RefundLine
from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    apply_currency,
    apply_payment_method,
    apply_period_channel_market,
    apply_sku,
    apply_snapshot_attr,
    apply_visitor_attr,
    format_rate,
)
from domains.reports.money_agg import (
    add_to_money,
    empty_money_buckets,
    money_breakdowns,
)
from domains.reports.schemas import ProductRow, ProductsResponse


def _empty_product() -> dict:
    return {
        "views": 0,
        "cart_adds": 0,
        "orders_created": 0,
        "orders_paid": 0,
        "paid_quantity": 0,
        "money": empty_money_buckets(),
        "payment_methods": set(),
    }


async def query_products(
    session: AsyncSession,
    filters: ReportFilters,
) -> ProductsResponse:
    items: dict[str, dict] = defaultdict(_empty_product)

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
        market_code=ProductView.market_code,
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
        market_code=CartAdd.market_code,
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

    created_stmt = (
        select(
            OrderLine.product_number,
            func.count(func.distinct(Order.order_id)),
        )
        .join(Order, OrderLine.order_id == Order.order_id)
        .where(OrderLine.is_paid_snapshot.is_(False))
        .where(OrderLine.product_number.isnot(None))
        .where(Order.created_event_id.isnot(None))
        .group_by(OrderLine.product_number)
    )
    created_stmt = apply_period_channel_market(
        created_stmt,
        filters,
        occurred_at=Order.created_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    created_stmt = apply_snapshot_attr(created_stmt, Order, filters)
    created_stmt = apply_payment_method(created_stmt, Order.payment_method, filters)
    created_stmt = apply_currency(created_stmt, Order.currency, filters)
    created_stmt = apply_sku(created_stmt, OrderLine.product_number, filters)
    created_rows = await session.execute(created_stmt)
    for sku, count in created_rows.all():
        items[str(sku)]["orders_created"] = int(count or 0)

    paid_stmt = (
        select(
            OrderLine.product_number,
            Order.currency,
            func.coalesce(func.sum(OrderLine.total_price), 0),
            func.count(func.distinct(Order.order_id)),
            func.coalesce(func.sum(OrderLine.quantity), 0),
        )
        .join(Order, OrderLine.order_id == Order.order_id)
        .where(OrderLine.is_paid_snapshot.is_(True))
        .where(OrderLine.product_number.isnot(None))
        .where(Order.paid_event_id.isnot(None))
        .group_by(OrderLine.product_number, Order.currency)
    )
    paid_stmt = apply_period_channel_market(
        paid_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    paid_stmt = apply_snapshot_attr(paid_stmt, Order, filters)
    paid_stmt = apply_payment_method(paid_stmt, Order.payment_method, filters)
    paid_stmt = apply_currency(paid_stmt, Order.currency, filters)
    paid_stmt = apply_sku(paid_stmt, OrderLine.product_number, filters)
    paid_rows = await session.execute(paid_stmt)
    for sku, currency, total, order_count, quantity in paid_rows.all():
        sku_key = str(sku)
        items[sku_key]["orders_paid"] += int(order_count or 0)
        items[sku_key]["paid_quantity"] += int(quantity or 0)
        add_to_money(
            items[sku_key]["money"],
            currency,
            gross=total,
            paid_count=order_count,
        )

    method_stmt = (
        select(OrderLine.product_number, Order.payment_method)
        .join(Order, OrderLine.order_id == Order.order_id)
        .where(OrderLine.is_paid_snapshot.is_(True))
        .where(OrderLine.product_number.isnot(None))
        .where(Order.paid_event_id.isnot(None))
        .where(Order.payment_method.isnot(None))
        .distinct()
    )
    method_stmt = apply_period_channel_market(
        method_stmt,
        filters,
        occurred_at=Order.paid_at,
        sales_channel_id=Order.sales_channel_id,
        market_code=Order.market_code,
    )
    method_stmt = apply_snapshot_attr(method_stmt, Order, filters)
    method_stmt = apply_payment_method(method_stmt, Order.payment_method, filters)
    method_stmt = apply_currency(method_stmt, Order.currency, filters)
    method_stmt = apply_sku(method_stmt, OrderLine.product_number, filters)
    method_rows = await session.execute(method_stmt)
    for sku, method in method_rows.all():
        items[str(sku)]["payment_methods"].add(str(method))

    refund_stmt = (
        select(
            RefundLine.product_number,
            Refund.currency,
            func.coalesce(func.sum(RefundLine.total_price), 0),
        )
        .join(Refund, RefundLine.refund_id == Refund.refund_id)
        .join(Order, Refund.order_id == Order.order_id)
        .where(RefundLine.product_number.isnot(None))
        .group_by(RefundLine.product_number, Refund.currency)
    )
    refund_stmt = apply_period_channel_market(
        refund_stmt,
        filters,
        occurred_at=Refund.refunded_at,
        sales_channel_id=Refund.sales_channel_id,
        market_code=Order.market_code,
    )
    refund_stmt = apply_snapshot_attr(refund_stmt, Order, filters)
    refund_stmt = apply_payment_method(refund_stmt, Refund.payment_method, filters)
    refund_stmt = apply_currency(refund_stmt, Refund.currency, filters)
    refund_stmt = apply_sku(refund_stmt, RefundLine.product_number, filters)
    refund_rows = await session.execute(refund_stmt)
    for sku, currency, total in refund_rows.all():
        add_to_money(items[str(sku)]["money"], currency, refunds=total)

    rows = [
        ProductRow(
            sku=sku,
            views=data["views"],
            cart_adds=data["cart_adds"],
            orders_created=data["orders_created"],
            orders_paid=data["orders_paid"],
            paid_quantity=data["paid_quantity"],
            money=money_breakdowns(data["money"]),
            view_to_paid_order=format_rate(data["orders_paid"], data["views"]),
            payment_methods=sorted(data["payment_methods"]),
        )
        for sku, data in sorted(items.items())
    ]
    return ProductsResponse(items=rows)
