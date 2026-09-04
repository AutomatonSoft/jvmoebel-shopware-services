from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import ColumnElement

AttributionModel = Literal["first_touch", "last_non_direct"]


class ReportFilters(BaseModel):
    period_from: datetime
    period_to: datetime
    sales_channel: str | None = None
    market: str | None = None
    source: str | None = None
    campaign: str | None = None
    sku: str | None = None
    channel: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    attribution_model: AttributionModel = "last_non_direct"
    period_end_inclusive: bool = True

    @property
    def first_or_last_prefix(self) -> str:
        if self.attribution_model == "first_touch":
            return "first_touch"
        return "last_non_direct"

    @property
    def snapshot_prefix(self) -> str:
        return f"attr_{self.first_or_last_prefix}"


def previous_period(filters: ReportFilters) -> ReportFilters:
    delta = filters.period_to - filters.period_from
    # model_copy - метод BaseModel (который является родителем ReportFilters)
    # делает новый экземпляр с теми же полями. Исходный filters не трогает
    # current-окно остаётся как пришло в запрос
    return filters.model_copy(
        update={
            "period_from": filters.period_from - delta,
            "period_to": filters.period_from,
            "period_end_inclusive": False,
        }
    )


def in_period(column, filters: ReportFilters) -> ColumnElement[bool]:
    # ColumnElement[bool] - часть SQL-выражения, которое будет использоваться в WHERE-условии
    lower = column >= filters.period_from
    # column — поле ORM, например Order.paid_at
    if filters.period_end_inclusive:
        # & здесь — оператор AND в SQL, который объединяет два условия
        # колонка ≥ начало и колонка ≤ конец
        return lower & (column <= filters.period_to)
    # колонка ≥ начало и колонка < конец
    return lower & (column < filters.period_to)


def attr_column(entity, filters: ReportFilters, field: str, *, snapshot: bool):
    # принимает только orm-модель таблиц-сущностей, не фактов
    # snapshot=False → колонка без attr_
    # snapshot=True → колонка с attr_
    prefix = filters.snapshot_prefix if snapshot else filters.first_or_last_prefix
    return getattr(entity, f"{prefix}_{field}")
