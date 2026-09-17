from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Query

from domains.reports.dependencies import parse_report_filters
from domains.reports.filters import AttributionModel, ReportFilters


def default_period_from() -> datetime:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=7)).replace(microsecond=0)


def default_period_to() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_dashboard_filters(
    period_from: datetime | None = None,
    period_to: datetime | None = None,
    sales_channel: Annotated[str | None, Query()] = None,
    attribution_model: AttributionModel = "last_non_direct",
) -> ReportFilters:
    if period_from is None:
        period_from = default_period_from()
    if period_to is None:
        period_to = default_period_to()
    channel = sales_channel.strip() if sales_channel else None
    return parse_report_filters(
        period_from=period_from,
        period_to=period_to,
        sales_channel=channel or None,
        attribution_model=attribution_model,
    )


def filter_query_string(filters: ReportFilters) -> str:
    params: dict[str, str] = {
        "period_from": filters.period_from.strftime("%Y-%m-%dT%H:%M:%S"),
        "period_to": filters.period_to.strftime("%Y-%m-%dT%H:%M:%S"),
        "attribution_model": filters.attribution_model,
    }
    if filters.sales_channel:
        params["sales_channel"] = filters.sales_channel
    return urlencode(params)


def datetime_local_value(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M")
