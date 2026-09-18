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
  lead_won: "Статус won",
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
  prepayment: "Предоплата",
  klarna: "Klarna",
};
