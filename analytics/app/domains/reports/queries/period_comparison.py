from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import PeriodComparisonQuery
from domains.reports.metrics import RATE_QUANT, format_change_pct
from domains.reports.money_agg import MONEY_QUANT, ZERO, money_to_api
from domains.reports.queries.overview import query_overview
from domains.reports.queries.payment_methods import query_payment_methods
from domains.reports.schemas import (
    Change,
    IntChange,
    MoneyBreakdown,
    MoneyChange,
    OverviewDelta,
    OverviewResponse,
    PaymentMethodDelta,
    PaymentMethodRow,
    PaymentMethodsComparison,
    PeriodComparisonResponse,
)

SECONDS_QUANT = Decimal("1")
EMPTY_MONEY = MoneyBreakdown(
    currency="",
    gross="0.0000",
    refunds="0.0000",
    net="0.0000",
    aov="0.0000",
)
EMPTY_METHOD = PaymentMethodRow(
    payment_method="",
    shown=0,
    selected=0,
    failed=0,
    selected_rate=None,
    orders_created=0,
    orders_paid=0,
    selected_to_paid=None,
    money=[],
)


def int_change(current: int, previous: int) -> IntChange:
    return IntChange(
        abs=current - previous,
        pct=format_change_pct(Decimal(current), Decimal(previous)),
    )


def decimal_change(
    current: Decimal | None,
    previous: Decimal | None,
    *,
    quant: Decimal,
) -> Change:
    if current is None and previous is None:
        abs_value = None
    else:
        abs_value = format(
            ((current or ZERO) - (previous or ZERO)).quantize(quant),
            "f",
        )
    pct = None
    if previous is not None:
        pct = format_change_pct(current or ZERO, previous)
    return Change(abs=abs_value, pct=pct)


def ratio_change(current: str | None, previous: str | None) -> Change:
    return decimal_change(
        None if current is None else Decimal(current),
        None if previous is None else Decimal(previous),
        quant=RATE_QUANT,
    )


def seconds_change(current: str | None, previous: str | None) -> Change:
    return decimal_change(
        None if current is None else Decimal(current),
        None if previous is None else Decimal(previous),
        quant=SECONDS_QUANT,
    )


def money_field_change(current: str, previous: str) -> Change:
    return decimal_change(Decimal(current), Decimal(previous), quant=MONEY_QUANT)


def money_changes(
    current: list[MoneyBreakdown],
    previous: list[MoneyBreakdown],
) -> list[MoneyChange]:
    current_by_currency = {row.currency: row for row in current}
    previous_by_currency = {row.currency: row for row in previous}
    currencies = sorted(set(current_by_currency) | set(previous_by_currency))
    rows: list[MoneyChange] = []
    for currency in currencies:
        current_row = current_by_currency.get(currency, EMPTY_MONEY)
        previous_row = previous_by_currency.get(currency, EMPTY_MONEY)
        rows.append(
            MoneyChange(
                currency=currency,
                gross=money_field_change(current_row.gross, previous_row.gross),
                refunds=money_field_change(
                    current_row.refunds,
                    previous_row.refunds,
                ),
                net=money_field_change(current_row.net, previous_row.net),
                aov=money_field_change(current_row.aov, previous_row.aov),
            )
        )
    return rows


def overview_delta(
    current: OverviewResponse,
    previous: OverviewResponse,
) -> OverviewDelta:
    return OverviewDelta(
        visitors=int_change(current.visitors, previous.visitors),
        sessions=int_change(current.sessions, previous.sessions),
        product_views=int_change(current.product_views, previous.product_views),
        cart_adds=int_change(current.cart_adds, previous.cart_adds),
        checkouts=int_change(current.checkouts, previous.checkouts),
        contacts=int_change(current.contacts, previous.contacts),
        leads=int_change(current.leads, previous.leads),
        orders_created=int_change(current.orders_created, previous.orders_created),
        orders_paid=int_change(current.orders_paid, previous.orders_paid),
        manual_sales=int_change(current.manual_sales, previous.manual_sales),
        money=money_changes(current.money, previous.money),
        session_to_lead=ratio_change(
            current.session_to_lead,
            previous.session_to_lead,
        ),
        session_to_paid_sale=ratio_change(
            current.session_to_paid_sale,
            previous.session_to_paid_sale,
        ),
        lead_to_paid_sale=ratio_change(
            current.lead_to_paid_sale,
            previous.lead_to_paid_sale,
        ),
        checkout_to_paid_order=ratio_change(
            current.checkout_to_paid_order,
            previous.checkout_to_paid_order,
        ),
        first_visit_to_lead_seconds=seconds_change(
            current.first_visit_to_lead_seconds,
            previous.first_visit_to_lead_seconds,
        ),
        first_visit_to_paid_sale_seconds=seconds_change(
            current.first_visit_to_paid_sale_seconds,
            previous.first_visit_to_paid_sale_seconds,
        ),
    )


def payment_method_delta(
    current: PaymentMethodRow,
    previous: PaymentMethodRow,
    *,
    payment_method: str,
) -> PaymentMethodDelta:
    return PaymentMethodDelta(
        payment_method=payment_method,
        shown=int_change(current.shown, previous.shown),
        selected=int_change(current.selected, previous.selected),
        failed=int_change(current.failed, previous.failed),
        selected_rate=ratio_change(current.selected_rate, previous.selected_rate),
        orders_created=int_change(current.orders_created, previous.orders_created),
        orders_paid=int_change(current.orders_paid, previous.orders_paid),
        selected_to_paid=ratio_change(
            current.selected_to_paid,
            previous.selected_to_paid,
        ),
        money=money_changes(current.money, previous.money),
    )


def payment_methods_comparison(
    current_rows: list[PaymentMethodRow],
    previous_rows: list[PaymentMethodRow],
) -> PaymentMethodsComparison:
    current_by_method = {row.payment_method: row for row in current_rows}
    previous_by_method = {row.payment_method: row for row in previous_rows}
    methods = sorted(set(current_by_method) | set(previous_by_method))
    return PaymentMethodsComparison(
        current=current_rows,
        previous=previous_rows,
        delta=[
            payment_method_delta(
                current_by_method.get(method, EMPTY_METHOD),
                previous_by_method.get(method, EMPTY_METHOD),
                payment_method=method,
            )
            for method in methods
        ],
    )


async def query_period_comparison(
    session: AsyncSession,
    query: PeriodComparisonQuery,
) -> PeriodComparisonResponse:
    current = await query_overview(session, query.current)
    previous = await query_overview(session, query.previous)
    current_methods = await query_payment_methods(session, query.current)
    previous_methods = await query_payment_methods(session, query.previous)
    return PeriodComparisonResponse(
        current=current,
        previous=previous,
        delta=overview_delta(current, previous),
        payment_methods=payment_methods_comparison(
            current_methods.items,
            previous_methods.items,
        ),
    )
