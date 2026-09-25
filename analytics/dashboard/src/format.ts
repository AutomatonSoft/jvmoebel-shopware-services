const numberRu = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dayRu = new Intl.NumberFormat("ru-RU", {
  maximumFractionDigits: 1,
});

const SYMBOLS: Record<string, string> = {
  EUR: "€",
  USD: "$",
  GBP: "£",
  CHF: "CHF",
  PLN: "zł",
};

export function formatRate(value: string | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(Number(value) * 100)} %`;
}

export function formatChangePct(value: string | null | undefined): string {
  if (value == null) return "—";
  const pct = Math.round(Number(value) * 100);
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct} %`;
}

export function formatPp(value: string | null | undefined): string {
  if (value == null) return "—";
  const points = Math.round(Number(value) * 100);
  const sign = points > 0 ? "+" : "";
  return `${sign}${points} п.п.`;
}

export function formatMoney(amount: string | null | undefined, currency: string): string {
  if (amount == null) return "—";
  const symbol = SYMBOLS[currency] ?? currency;
  return `${numberRu.format(Number(amount))} ${symbol}`;
}

export function formatMoneyList(
  rows: { currency: string; net?: string; gross?: string; aov?: string }[],
  field: "net" | "gross" | "aov" = "net",
): string {
  if (!rows.length) return "—";
  return rows.map((row) => formatMoney(row[field], row.currency)).join(" · ");
}

export function formatDays(seconds: string | null | undefined): string {
  if (seconds == null) return "—";
  return `${dayRu.format(Number(seconds) / 86400)} дн.`;
}

export function formatInt(value: number): string {
  return new Intl.NumberFormat("ru-RU").format(value);
}

export function formatSignedInt(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatInt(value)}`;
}

export function formatDateTime(iso: string): string {
  return `${new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(iso))} UTC`;
}

export function formatRange(from: string, to: string): string {
  const fmt = new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  });
  return `${fmt.format(new Date(from))} – ${fmt.format(new Date(to))}`;
}

export function tone(value: number | string | null | undefined): string {
  if (value == null || value === "") return "";
  const amount = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(amount) || amount === 0) return "";
  return amount > 0 ? "up" : "down";
}

export const FUNNEL_LABELS: Record<string, string> = {
  session: "Сессии",
  product_view: "Просмотр товара",
  add_to_cart: "В корзину",
  checkout_started: "Оформление",
  order_created: "Заказ создан",
  order_paid: "Заказ оплачен",
  contact_intent: "Нажатие «написать»",
  contact_received: "Подтверждённое обращение",
  lead_created: "Лид",
  lead_won: "Сделка выиграна",
  paid_sale: "Оплаченная продажа",
};

export const CHANNEL_LABELS: Record<string, string> = {
  form: "Форма",
  email: "Email",
  whatsapp: "WhatsApp",
  phone: "Телефон",
};

export const EVENT_LABELS: Record<string, string> = {
  session_started: "Старт сессии",
  product_viewed: "Просмотр товара",
  add_to_cart: "Добавление в корзину",
  checkout_started: "Старт оформления",
  payment_methods_shown: "Показаны способы оплаты",
  payment_method_selected: "Выбран способ оплаты",
  payment_failed: "Ошибка оплаты",
  contact_intent: "Намерение написать",
  lead_created: "Создан лид",
  contact_received: "Обращение",
  lead_status_changed: "Статус лида",
  order_created: "Заказ создан",
  order_paid: "Заказ оплачен",
  order_updated: "Заказ обновлён",
  order_cancelled: "Заказ отменён",
  refund_created: "Возврат",
  manual_sale_created: "Ручная продажа",
  manual_sale_cancelled: "Ручная продажа отменена",
  customer_linked: "Покупатель связан",
};

export const ENTITY_LABELS: Record<string, string> = {
  visitor: "Посетитель",
  session: "Сессия",
  lead: "Лид",
  order: "Заказ",
  customer: "Покупатель",
  contact: "Обращение",
  manual_sale: "Ручная продажа",
};

export const PAYMENT_LABELS: Record<string, string> = {
  paypal: "PayPal",
  invoice: "Счёт",
  installment: "Рассрочка",
  creditcard: "Карта",
  card: "Карта",
  prepayment: "Предоплата",
  klarna: "Klarna",
};

export const ATTRIBUTION_LABELS = {
  last_non_direct: "Последний источник",
  first_touch: "Первый источник",
} as const;

export const SOURCE_LABELS: Record<string, string> = {
  google_ads: "Google Ads",
  google: "Google",
  seo: "SEO",
  social: "Соцсети",
  email: "Email",
  newsletter: "Email",
  paid: "Платная реклама",
  referral: "Реферальный",
  affiliate: "Реферальный",
  direct: "Прямой заход",
  other: "Другое",
  facebook: "Facebook",
  instagram: "Instagram",
  bing: "Bing",
  pinterest: "Pinterest",
  youtube: "YouTube",
};

const LEAD_STATUS_LABELS: Record<string, string> = {
  new: "новый",
  contacted: "связались",
  offer_sent: "оферта отправлена",
  won: "сделка выиграна",
  lost: "потерян",
};

const CONTACT_TYPE_LABELS: Record<string, string> = {
  offer_request: "запрос предложения",
  contact_form: "форма",
  callback_request: "обратный звонок",
  whatsapp_message: "WhatsApp",
  direct_email: "письмо",
  qualified_call: "звонок",
};

export function labelSource(source: string | null | undefined): string {
  if (!source) return "—";
  return SOURCE_LABELS[source] ?? source;
}

export function labelPayment(method: string | null | undefined): string {
  if (!method) return "—";
  return PAYMENT_LABELS[method] ?? method;
}

export function shopName(
  shops: { id: string; label: string }[],
  salesChannelId: string,
): string {
  return shops.find((shop) => shop.id === salesChannelId)?.label ?? salesChannelId;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function textOf(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function payloadText(payload: Record<string, unknown>, key: string): string | null {
  return textOf(payload[key]);
}

function joinParts(parts: Array<string | null | undefined>): string {
  return parts.filter((part): part is string => Boolean(part)).join(", ");
}

function sessionOrigin(trafficSource: string | null | undefined): string | null {
  if (!trafficSource) return null;
  if (trafficSource === "direct") return "Прямой заход";
  return `Пришёл из ${labelSource(trafficSource)}`;
}

function productName(payload: Record<string, unknown>): string | null {
  return payloadText(payload, "name") ?? payloadText(payload, "sku");
}

function payloadPrice(payload: Record<string, unknown>): string | null {
  const amount =
    payloadText(payload, "total_amount") ??
    payloadText(payload, "unit_price") ??
    payloadText(payload, "amount") ??
    payloadText(payload, "refund_amount");
  if (!amount) return null;
  return formatMoney(amount, payloadText(payload, "currency") ?? "EUR");
}

export function summarizeJourneyEvent(
  payload: Record<string, unknown>,
  eventType: string,
  trafficSource?: string | null,
  invalidReason?: string | null,
): string {
  const utm = asRecord(payload.utm);
  const campaign = utm ? payloadText(utm, "utm_campaign") : null;
  const product = productName(payload);
  const sku = payloadText(payload, "sku") ?? payloadText(payload, "product_number");
  const price = payloadPrice(payload);
  const orderNumber = payloadText(payload, "order_number");
  const paymentRaw = payloadText(payload, "payment_method");
  const payment = paymentRaw ? labelPayment(paymentRaw) : null;
  const channelRaw =
    payloadText(payload, "channel") ?? payloadText(payload, "contact_channel");
  const channel = channelRaw
    ? (CHANNEL_LABELS[channelRaw] ?? channelRaw)
    : null;
  const statusRaw = payloadText(payload, "new_status");
  const status = statusRaw ? (LEAD_STATUS_LABELS[statusRaw] ?? statusRaw) : null;
  const contactTypeRaw = payloadText(payload, "contact_type");
  const contactType = contactTypeRaw
    ? (CONTACT_TYPE_LABELS[contactTypeRaw] ?? contactTypeRaw)
    : null;
  const methods = Array.isArray(payload.methods)
    ? payload.methods
        .filter((item): item is string => typeof item === "string")
        .map((item) => labelPayment(item))
        .join(", ")
    : null;

  switch (eventType) {
    case "session_started":
      return joinParts([
        sessionOrigin(trafficSource),
        campaign ? `кампания ${campaign}` : null,
      ]);
    case "product_viewed":
      return joinParts([product ? `Смотрел ${product}` : null, price]);
    case "add_to_cart":
      return joinParts([product ? `В корзину: ${product}` : null, price]);
    case "checkout_started":
      return joinParts(["Начал оформление", price]);
    case "payment_methods_shown":
      return methods ? `Показаны: ${methods}` : "";
    case "payment_method_selected":
      return payment ? `Выбрал ${payment}` : "";
    case "payment_failed":
      return joinParts([
        payment ? `Ошибка оплаты ${payment}` : "Ошибка оплаты",
        payloadText(payload, "error_code"),
      ]);
    case "contact_intent":
      return joinParts([channel ? `Нажал «написать» (${channel})` : null]);
    case "lead_created":
      return joinParts(["Создан лид", channel, contactType]);
    case "contact_received":
      return joinParts([channel, contactType, sku]);
    case "lead_status_changed":
      return status ? `Статус: ${status}` : "";
    case "order_created":
      return joinParts([
        orderNumber ? `Заказ ${orderNumber} создан` : "Заказ создан",
        payment,
        price,
      ]);
    case "order_paid":
      return joinParts([
        orderNumber ? `Заказ ${orderNumber} оплачен` : "Заказ оплачен",
        payment,
        price,
      ]);
    case "order_updated":
      return joinParts([orderNumber ? `Заказ ${orderNumber} обновлён` : null, payment]);
    case "order_cancelled":
      return orderNumber ? `Заказ ${orderNumber} отменён` : "Заказ отменён";
    case "refund_created":
      return joinParts([
        orderNumber ? `Возврат по заказу ${orderNumber}` : "Возврат",
        price,
        invalidReason === "currency_mismatch"
          ? "валюта не совпадает с заказом"
          : null,
      ]);
    case "manual_sale_created": {
      const reference = payloadText(payload, "reference");
      return joinParts([
        reference ? `Ручная продажа ${reference}` : "Ручная продажа",
        price,
      ]);
    }
    case "manual_sale_cancelled":
      return "Ручная продажа отменена";
    case "customer_linked":
      return "Покупатель связан с посетителем";
    default:
      return joinParts([product, orderNumber, payment, campaign]);
  }
}
