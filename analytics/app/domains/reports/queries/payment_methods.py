from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.facts import PaymentMethodEvent
from domains.reports.filters import ReportFilters
from domains.reports.metrics import apply_period_channel_market, format_rate
from domains.reports.schemas import PaymentMethodRow, PaymentMethodsResponse


# считает shown/selected/failed по каждому способу оплаты и rate = selected/shown
async def query_payment_methods(
    session: AsyncSession,
    filters: ReportFilters,
) -> PaymentMethodsResponse:
    shown = func.count(case((PaymentMethodEvent.kind == "shown", 1)))
    selected = func.count(case((PaymentMethodEvent.kind == "selected", 1)))
    failed = func.count(case((PaymentMethodEvent.kind == "failed", 1)))
    stmt = (
        select(
            PaymentMethodEvent.payment_method,
            shown,
            selected,
            failed,
        )
        .select_from(PaymentMethodEvent)
        .group_by(PaymentMethodEvent.payment_method)
    )
    stmt = apply_period_channel_market(
        stmt,
        filters,
        occurred_at=PaymentMethodEvent.occurred_at,
        sales_channel_id=PaymentMethodEvent.sales_channel_id,
    )
    if filters.payment_method is not None:
        stmt = stmt.where(
            PaymentMethodEvent.payment_method == filters.payment_method
        )
    result = await session.execute(stmt)
    items = []
    for method, shown_count, selected_count, failed_count in result.all():
        shown_int = int(shown_count)
        selected_int = int(selected_count)
        items.append(
            PaymentMethodRow(
                payment_method=method,
                shown=shown_int,
                selected=selected_int,
                failed=int(failed_count),
                selected_rate=format_rate(
                    selected_int,
                    shown_int,
                ),
            )
        )
    items.sort(key=lambda row: row.payment_method)
    return PaymentMethodsResponse(items=items)
