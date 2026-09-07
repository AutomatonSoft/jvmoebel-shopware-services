from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    count_cart_adders,
    count_checkout_visitors,
    count_contact_intent_visitors,
    count_contacts,
    count_leads,
    count_leads_won,
    count_manual_sales,
    count_orders_created,
    count_orders_paid,
    count_product_viewers,
    count_sessions,
    format_rate,
)
from domains.reports.schemas import FunnelResponse, FunnelStep

ECOMMERCE_KEYS = (
    "session",
    "product_view",
    "add_to_cart",
    "checkout_started",
    "order_created",
    "order_paid",
)
LEAD_KEYS = (
    "session",
    "contact_intent",
    "contact_received",
    "lead_created",
    "lead_won",
    "paid_sale",
)


def build_steps(keys: tuple[str, ...], counts: list[int]) -> list[FunnelStep]:
    steps: list[FunnelStep] = []
    previous: int | None = None
    for key, count in zip(keys, counts, strict=True):
        conversion = (
            None if previous is None else format_rate(count, previous)
        )
        steps.append(
            FunnelStep(
                key=key,
                count=count,
                conversion_from_previous=conversion,
            )
        )
        previous = count
    return steps


async def query_funnel(
    session: AsyncSession,
    filters: ReportFilters,
) -> FunnelResponse:
    sessions = await count_sessions(session, filters)
    orders_paid = await count_orders_paid(session, filters)
    manual_sales = await count_manual_sales(session, filters)
    return FunnelResponse(
        ecommerce=build_steps(
            ECOMMERCE_KEYS,
            [
                sessions,
                await count_product_viewers(session, filters),
                await count_cart_adders(session, filters),
                await count_checkout_visitors(session, filters),
                await count_orders_created(session, filters),
                orders_paid,
            ],
        ),
        lead=build_steps(
            LEAD_KEYS,
            [
                sessions,
                await count_contact_intent_visitors(session, filters),
                await count_contacts(session, filters),
                await count_leads(session, filters),
                await count_leads_won(session, filters),
                orders_paid + manual_sales,
            ],
        ),
    )
