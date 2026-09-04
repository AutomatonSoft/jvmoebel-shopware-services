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
    leads: int
    orders_created: int
    orders_paid: int
    money: list[MoneyBreakdown]


class FunnelResponse(BaseModel):
    visitors: int
    sessions: int
    product_viewers: int
    cart_adders: int
    checkouts: int
    leads: int
    orders_created: int
    orders_paid: int


class SourceRow(BaseModel):
    source: str
    visitors: int
    sessions: int
    leads: int
    orders_paid: int
    money: list[MoneyBreakdown]


class SourcesResponse(BaseModel):
    items: list[SourceRow]


class ContactChannelRow(BaseModel):
    channel: str
    contacts: int


class ContactChannelsResponse(BaseModel):
    items: list[ContactChannelRow]


class ProductRow(BaseModel):
    sku: str
    views: int
    cart_adds: int
    paid_quantity: int


class ProductsResponse(BaseModel):
    items: list[ProductRow]


class PaymentMethodRow(BaseModel):
    payment_method: str
    shown: int
    selected: int
    failed: int
    selected_rate: str | None


class PaymentMethodsResponse(BaseModel):
    items: list[PaymentMethodRow]


class PeriodComparisonResponse(BaseModel):
    current: OverviewResponse
    previous: OverviewResponse
