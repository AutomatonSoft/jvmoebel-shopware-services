export type Money = {
  currency: string;
  gross: string;
  refunds: string;
  net: string;
  aov: string;
};

export type Overview = {
  visitors: number;
  sessions: number;
  product_views: number;
  cart_adds: number;
  checkouts: number;
  contacts: number;
  leads: number;
  orders_created: number;
  orders_paid: number;
  manual_sales: number;
  money: Money[];
  session_to_lead: string | null;
  session_to_paid_sale: string | null;
  lead_to_paid_sale: string | null;
  checkout_to_paid_order: string | null;
  first_visit_to_lead_seconds: string | null;
  first_visit_to_paid_sale_seconds: string | null;
};

export type FunnelStep = {
  key: string;
  count: number;
  conversion_from_previous: string | null;
};

export type DailyPoint = {
  date: string;
  orders_paid: number;
  manual_sales: number;
  paid_sales: number;
  money: Money[];
};

export type SourceRow = {
  source: string;
  campaign: string | null;
  visitors: number;
  sessions: number;
  contacts: number;
  leads: number;
  orders_created: number;
  orders_paid: number;
  manual_sales: number;
  money: Money[];
  session_to_lead: string | null;
  session_to_paid_sale: string | null;
  lead_to_paid_sale: string | null;
  first_visit_to_lead_seconds: string | null;
  first_visit_to_paid_sale_seconds: string | null;
};

export type ChannelRow = {
  channel: string;
  intents: number;
  contacts: number;
  leads: number;
  orders_paid: number;
  manual_sales: number;
  money: Money[];
  contact_to_lead: string | null;
  lead_to_paid_sale: string | null;
};

export type ProductRow = {
  sku: string;
  views: number;
  cart_adds: number;
  orders_created: number;
  orders_paid: number;
  paid_quantity: number;
  money: Money[];
  view_to_paid_order: string | null;
  payment_methods: string[];
};

export type PaymentRow = {
  payment_method: string;
  shown: number;
  selected: number;
  failed: number;
  selected_rate: string | null;
  orders_created: number;
  orders_paid: number;
  selected_to_paid: string | null;
  money: Money[];
};

export type Change = { abs: string | null; pct: string | null };
export type IntChange = { abs: number; pct: string | null };

export type JourneyHit = {
  entity_type: string;
  id: string;
  sales_channel_id: string;
  occurred_at: string;
};

export type JourneyEvent = {
  event_id: string;
  event_type: string;
  occurred_at: string;
  received_at: string;
  source: string;
  sales_channel_id: string;
  visitor_id: string | null;
  session_id: string | null;
  lead_id: string | null;
  order_id: string | null;
  customer_id: string | null;
  contact_id: string | null;
  manual_sale_id: string | null;
  refund_id: string | null;
  traffic_source: string | null;
  payload: Record<string, unknown>;
};

export type FunnelResponse = { ecommerce: FunnelStep[]; lead: FunnelStep[] };
export type DailyResponse = { items: DailyPoint[] };
export type SourcesResponse = { items: SourceRow[] };
export type ChannelsResponse = { items: ChannelRow[] };
export type ProductsResponse = { items: ProductRow[] };
export type PaymentsResponse = { items: PaymentRow[] };
export type JourneySearchResponse = { items: JourneyHit[] };
export type JourneyResponse = { events: JourneyEvent[] };

export type PeriodComparison = {
  current: Overview;
  previous: Overview;
  delta: {
    visitors: IntChange;
    sessions: IntChange;
    product_views: IntChange;
    cart_adds: IntChange;
    checkouts: IntChange;
    contacts: IntChange;
    leads: IntChange;
    orders_created: IntChange;
    orders_paid: IntChange;
    manual_sales: IntChange;
    money: {
      currency: string;
      gross: Change;
      refunds: Change;
      net: Change;
      aov: Change;
    }[];
    session_to_lead: Change;
    session_to_paid_sale: Change;
    lead_to_paid_sale: Change;
    checkout_to_paid_order: Change;
    first_visit_to_lead_seconds: Change;
    first_visit_to_paid_sale_seconds: Change;
  };
  payment_methods: {
    current: PaymentRow[];
    previous: PaymentRow[];
    delta: {
      payment_method: string;
      shown: IntChange;
      selected: IntChange;
      failed: IntChange;
      selected_rate: Change;
      orders_created: IntChange;
      orders_paid: IntChange;
      selected_to_paid: Change;
      money: {
        currency: string;
        net: Change;
      }[];
    }[];
  };
};

export type Shop = { id: string; label: string };

export type Filters = {
  period_from: string;
  period_to: string;
  sales_channel: string;
  attribution_model: "first_touch" | "last_non_direct";
};
