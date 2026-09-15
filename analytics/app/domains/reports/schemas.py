from pydantic import BaseModel


class MoneyBreakdown(BaseModel):
    currency: str
    gross: str
    refunds: str
    net: str
    aov: str


class OverviewResponse(BaseModel):
    visitors: int
    sessions: int
    product_views: int
    cart_adds: int
    checkouts: int
    contacts: int
    leads: int
    orders_created: int
    orders_paid: int
    manual_sales: int
    money: list[MoneyBreakdown]
    session_to_lead: str | None
    session_to_paid_sale: str | None
    lead_to_paid_sale: str | None
    checkout_to_paid_order: str | None
    first_visit_to_lead_seconds: str | None
    first_visit_to_paid_sale_seconds: str | None


class FunnelStep(BaseModel):
    key: str
    count: int
    conversion_from_previous: str | None


class FunnelResponse(BaseModel):
    ecommerce: list[FunnelStep]
    lead: list[FunnelStep]


class SourceRow(BaseModel):
    source: str
    campaign: str | None
    visitors: int
    sessions: int
    contacts: int
    leads: int
    orders_created: int
    orders_paid: int
    manual_sales: int
    money: list[MoneyBreakdown]
    session_to_lead: str | None
    session_to_paid_sale: str | None
    lead_to_paid_sale: str | None
    first_visit_to_lead_seconds: str | None
    first_visit_to_paid_sale_seconds: str | None


class SourcesResponse(BaseModel):
    items: list[SourceRow]


class ContactChannelRow(BaseModel):
    channel: str
    intents: int
    contacts: int
    leads: int
    orders_paid: int
    manual_sales: int
    money: list[MoneyBreakdown]
    contact_to_lead: str | None
    lead_to_paid_sale: str | None


class ContactChannelsResponse(BaseModel):
    items: list[ContactChannelRow]


class ProductRow(BaseModel):
    sku: str
    views: int
    cart_adds: int
    orders_created: int
    orders_paid: int
    paid_quantity: int
    money: list[MoneyBreakdown]
    view_to_paid_order: str | None
    payment_methods: list[str]


class ProductsResponse(BaseModel):
    items: list[ProductRow]


class PaymentMethodRow(BaseModel):
    payment_method: str
    shown: int
    selected: int
    failed: int
    selected_rate: str | None
    orders_created: int
    orders_paid: int
    selected_to_paid: str | None
    money: list[MoneyBreakdown]


class PaymentMethodsResponse(BaseModel):
    items: list[PaymentMethodRow]


class Change(BaseModel):
    abs: str | None
    pct: str | None


class IntChange(BaseModel):
    abs: int
    pct: str | None


class MoneyChange(BaseModel):
    currency: str
    gross: Change
    refunds: Change
    net: Change
    aov: Change


class OverviewDelta(BaseModel):
    visitors: IntChange
    sessions: IntChange
    product_views: IntChange
    cart_adds: IntChange
    checkouts: IntChange
    contacts: IntChange
    leads: IntChange
    orders_created: IntChange
    orders_paid: IntChange
    manual_sales: IntChange
    money: list[MoneyChange]
    session_to_lead: Change
    session_to_paid_sale: Change
    lead_to_paid_sale: Change
    checkout_to_paid_order: Change
    first_visit_to_lead_seconds: Change
    first_visit_to_paid_sale_seconds: Change


class PaymentMethodDelta(BaseModel):
    payment_method: str
    shown: IntChange
    selected: IntChange
    failed: IntChange
    selected_rate: Change
    orders_created: IntChange
    orders_paid: IntChange
    selected_to_paid: Change
    money: list[MoneyChange]


class PaymentMethodsComparison(BaseModel):
    current: list[PaymentMethodRow]
    previous: list[PaymentMethodRow]
    delta: list[PaymentMethodDelta]


class PeriodComparisonResponse(BaseModel):
    current: OverviewResponse
    previous: OverviewResponse
    delta: OverviewDelta
    payment_methods: PaymentMethodsComparison
