from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.handlers.add_to_cart import handle_add_to_cart
from domains.projections.handlers.checkout_started import handle_checkout_started
from domains.projections.handlers.contact_intent import handle_contact_intent
from domains.projections.handlers.contact_received import handle_contact_received
from domains.projections.handlers.customer_linked import handle_customer_linked
from domains.projections.handlers.lead_created import handle_lead_created
from domains.projections.handlers.lead_status_changed import handle_lead_status_changed
from domains.projections.handlers.manual_sale_cancelled import handle_manual_sale_cancelled
from domains.projections.handlers.manual_sale_created import handle_manual_sale_created
from domains.projections.handlers.manual_sale_updated import handle_manual_sale_updated
from domains.projections.handlers.order_cancelled import handle_order_cancelled
from domains.projections.handlers.order_created import handle_order_created
from domains.projections.handlers.order_paid import handle_order_paid
from domains.projections.handlers.order_updated import handle_order_updated
from domains.projections.handlers.payment_failed import handle_payment_failed
from domains.projections.handlers.payment_method_selected import handle_payment_method_selected
from domains.projections.handlers.payment_methods_shown import handle_payment_methods_shown
from domains.projections.handlers.product_viewed import handle_product_viewed
from domains.projections.handlers.refund_created import handle_refund_created
from domains.projections.handlers.session_started import handle_session_started
from domains.projections.models.journal import Event

# EventHandler - функция, которая принимает сессию и событие и возвращает асинхронную задачу
EventHandler = Callable[[AsyncSession, Event], Awaitable[None]]

HANDLERS: dict[str, EventHandler] = {
    "session_started": handle_session_started,
    "product_viewed": handle_product_viewed,
    "add_to_cart": handle_add_to_cart,
    "checkout_started": handle_checkout_started,
    "payment_methods_shown": handle_payment_methods_shown,
    "payment_method_selected": handle_payment_method_selected,
    "payment_failed": handle_payment_failed,
    "contact_intent": handle_contact_intent,
    "contact_received": handle_contact_received,
    "lead_created": handle_lead_created,
    "lead_status_changed": handle_lead_status_changed,
    "customer_linked": handle_customer_linked,
    "order_created": handle_order_created,
    "order_updated": handle_order_updated,
    "order_paid": handle_order_paid,
    "order_cancelled": handle_order_cancelled,
    "manual_sale_created": handle_manual_sale_created,
    "manual_sale_updated": handle_manual_sale_updated,
    "manual_sale_cancelled": handle_manual_sale_cancelled,
    "refund_created": handle_refund_created,
}


async def dispatch(session: AsyncSession, event: Event) -> None:
    handler = HANDLERS.get(event.event_type)
    if handler is None:
        raise RuntimeError(f"No projection handler for event_type={event.event_type!r}")
    await handler(session, event)
