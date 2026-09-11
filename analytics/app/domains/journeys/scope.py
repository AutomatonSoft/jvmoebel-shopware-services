from sqlalchemy import ColumnElement, or_, select

from domains.projections.models.entities import CustomerLink, Lead, ManualSale, Order
from domains.projections.models.journal import Event


# возвращает SQL-выражение, которое в итоге является условием True/False
def customer_events_clause(customer_id: str) -> ColumnElement[bool]:
    visitor_ids = select(CustomerLink.visitor_id).where(
        CustomerLink.customer_id == customer_id,
    )
    order_ids = select(Order.order_id).where(Order.customer_id == customer_id)
    lead_ids = select(Lead.lead_id).where(Lead.customer_id == customer_id)
    sale_ids = select(ManualSale.manual_sale_id).where(ManualSale.customer_id == customer_id)
    # событие попадает в путь, если хотя бы одно из условий истинно
    return or_(
        Event.customer_id == customer_id,
        Event.visitor_id.in_(visitor_ids),
        Event.order_id.in_(order_ids),
        Event.lead_id.in_(lead_ids),
        Event.manual_sale_id.in_(sale_ids),
    )


def lead_events_clause(lead_id: str) -> ColumnElement[bool]:
    visitor_ids = select(Lead.visitor_id).where(
        Lead.lead_id == lead_id,
        Lead.visitor_id.isnot(None),
    )
    order_ids = select(Order.order_id).where(Order.lead_id == lead_id)
    sale_ids = select(ManualSale.manual_sale_id).where(
        ManualSale.lead_id == lead_id,
    )
    return or_(
        Event.lead_id == lead_id,
        Event.visitor_id.in_(visitor_ids),
        Event.order_id.in_(order_ids),
        Event.manual_sale_id.in_(sale_ids),
    )


def order_events_clause(order_id: str) -> ColumnElement[bool]:
    visitor_ids = select(Order.visitor_id).where(
        Order.order_id == order_id,
        Order.visitor_id.isnot(None),
    )
    cart_ids = select(Order.cart_id).where(
        Order.order_id == order_id,
        Order.cart_id.isnot(None),
    )
    lead_ids = select(Order.lead_id).where(
        Order.order_id == order_id,
        Order.lead_id.isnot(None),
    )
    return or_(
        Event.order_id == order_id,
        Event.visitor_id.in_(visitor_ids),
        Event.cart_id.in_(cart_ids),
        Event.lead_id.in_(lead_ids),
    )
