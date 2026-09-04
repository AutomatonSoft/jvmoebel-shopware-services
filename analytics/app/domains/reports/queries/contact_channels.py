from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.entities import Lead
from domains.projections.models.facts import Contact
from domains.reports.filters import ReportFilters
from domains.reports.metrics import apply_period_channel_market, apply_snapshot_attr
from domains.reports.schemas import ContactChannelRow, ContactChannelsResponse


async def query_contact_channels(
    session: AsyncSession,
    filters: ReportFilters,
) -> ContactChannelsResponse:
    stmt = (
        select(Contact.contact_channel, func.count())
        .select_from(Contact)
        .group_by(Contact.contact_channel)
    )
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
    result = await session.execute(stmt)
    items = [
        ContactChannelRow(channel=channel, contacts=int(count or 0))
        for channel, count in result.all()
    ]
    items.sort(key=lambda row: row.channel)
    return ContactChannelsResponse(items=items)
