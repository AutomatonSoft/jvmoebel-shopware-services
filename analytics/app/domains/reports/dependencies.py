from datetime import datetime, timezone

from domains.base.exceptions import BadRequestException
from domains.reports.filters import (
    AttributionModel,
    PeriodComparisonQuery,
    ReportFilters,
)


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


def parse_period_comparison_filters(
    period_from: datetime,
    period_to: datetime,
    compare_from: datetime | None = None,
    compare_to: datetime | None = None,
    sales_channel: str | None = None,
    market: str | None = None,
    source: str | None = None,
    campaign: str | None = None,
    sku: str | None = None,
    channel: str | None = None,
    payment_method: str | None = None,
    currency: str | None = None,
    attribution_model: AttributionModel = "last_non_direct",
) -> PeriodComparisonQuery:
    current = parse_report_filters(
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
    if compare_from is None or compare_to is None:
        raise BadRequestException(
            detail="compare_from and compare_to are required",
        )
    compare_from = _ensure_aware(compare_from)
    compare_to = _ensure_aware(compare_to)
    if compare_from > compare_to:
        raise BadRequestException(detail="compare_from must be <= compare_to")
    return PeriodComparisonQuery(
        current=current,
        previous=current.model_copy(
            update={
                "period_from": compare_from,
                "period_to": compare_to,
            }
        ),
    )
