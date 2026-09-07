from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    avg_first_visit_to_lead_seconds,
    avg_first_visit_to_paid_sale_seconds,
    count_cart_adds,
    count_checkouts,
    count_contacts,
    count_leads,
    count_manual_sales,
    count_orders_created,
    count_orders_paid,
    count_product_views,
    count_sessions,
    count_visitors,
    format_rate,
)
from domains.reports.money_agg import aggregate_money
from domains.reports.schemas import OverviewResponse


async def query_overview(
    session: AsyncSession,
    filters: ReportFilters,
) -> OverviewResponse:
    sessions = await count_sessions(session, filters)
    checkouts = await count_checkouts(session, filters)
    leads = await count_leads(session, filters)
    orders_paid = await count_orders_paid(session, filters)
    manual_sales = await count_manual_sales(session, filters)
    paid_sales = orders_paid + manual_sales
    return OverviewResponse(
        visitors=await count_visitors(session, filters),
        sessions=sessions,
        product_views=await count_product_views(session, filters),
        cart_adds=await count_cart_adds(session, filters),
        checkouts=checkouts,
        contacts=await count_contacts(session, filters),
        leads=leads,
        orders_created=await count_orders_created(session, filters),
        orders_paid=orders_paid,
        manual_sales=manual_sales,
        money=await aggregate_money(session, filters),
        session_to_lead=format_rate(leads, sessions),
        session_to_paid_sale=format_rate(paid_sales, sessions),
        lead_to_paid_sale=format_rate(paid_sales, leads),
        checkout_to_paid_order=format_rate(orders_paid, checkouts),
        first_visit_to_lead_seconds=await avg_first_visit_to_lead_seconds(
            session,
            filters,
        ),
        first_visit_to_paid_sale_seconds=await avg_first_visit_to_paid_sale_seconds(
            session,
            filters,
        ),
    )
