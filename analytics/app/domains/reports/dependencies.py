from datetime import datetime, timezone

from domains.base.exceptions import BadRequestException
from domains.reports.filters import AttributionModel, ReportFilters


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def parse_report_filters(
    period_from: datetime,
    period_to: datetime,
    sales_channel: str | None = None,
    market: str | None = None,
    source: str | None = None,
    campaign: str | None = None,
    sku: str | None = None,
    channel: str | None = None,
    payment_method: str | None = None,
    currency: str | None = None,
    attribution_model: AttributionModel = "last_non_direct",
) -> ReportFilters:
    period_from = _ensure_aware(period_from)
    period_to = _ensure_aware(period_to)
    if period_from > period_to:
        raise BadRequestException(detail="period_from must be <= period_to")
    return ReportFilters(
        period_from=period_from,
        period_to=period_to,
        sales_channel=sales_channel,
        market=market,
        source=source,
        campaign=campaign,
        sku=sku,
        channel=channel,
        payment_method=payment_method,
        currency=currency,
        attribution_model=attribution_model,
    )
