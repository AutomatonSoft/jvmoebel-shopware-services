import type {
  ChannelsResponse,
  DailyResponse,
  Filters,
  FunnelResponse,
  JourneyResponse,
  JourneySearchResponse,
  Overview,
  PaymentsResponse,
  PeriodComparison,
  ProductsResponse,
  Shop,
  SourcesResponse,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function errorMessage(status: number, detail: unknown): string {
  if (status === 401) return "Нет доступа. Обновите страницу и войдите.";
  if (status === 400) return "Проверьте период и фильтры.";
  if (status === 404) return "Ничего не найдено.";
  if (status === 422) return "Некорректные параметры запроса.";
  if (typeof detail === "string" && detail) return detail;
  return "Не удалось загрузить данные. Попробуйте ещё раз.";
}

const DASHBOARD_PREFIX = "/dashboard";
const AUTH_RETURN_KEY = "dashboard-auth-return";

function dashboardRelativePath(): string {
  const { pathname, search, hash } = window.location;
  let rest = pathname;
  if (rest === DASHBOARD_PREFIX || rest === `${DASHBOARD_PREFIX}/`) {
    rest = "/";
  } else if (rest.startsWith(`${DASHBOARD_PREFIX}/`)) {
    rest = rest.slice(DASHBOARD_PREFIX.length);
  }
  if (!rest.startsWith("/")) rest = `/${rest}`;
  return `${rest}${search}${hash}`;
}

export function safeDashboardNext(raw: string | null): string | null {
  if (!raw) return null;
  let next = raw;
  if (next.startsWith(`${DASHBOARD_PREFIX}/`)) {
    next = next.slice(DASHBOARD_PREFIX.length);
  } else if (next === DASHBOARD_PREFIX || next === `${DASHBOARD_PREFIX}/`) {
    return null;
  }
  if (!next.startsWith("/") || next.startsWith("//") || next === "/") {
    return null;
  }
  return next;
}

function redirectToDashboardLogin(): void {
  const next = safeDashboardNext(dashboardRelativePath());
  if (!next || sessionStorage.getItem(AUTH_RETURN_KEY) === "1") return;
  sessionStorage.setItem(AUTH_RETURN_KEY, "1");
  window.location.assign(
    `${DASHBOARD_PREFIX}/?next=${encodeURIComponent(next)}`,
  );
}

async function request<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  const response = await fetch(url.toString(), { credentials: "same-origin" });
  if (!response.ok) {
    if (response.status === 401) {
      redirectToDashboardLogin();
      throw new ApiError(401, errorMessage(401, undefined));
    }
    let detail: unknown;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, errorMessage(response.status, detail));
  }
  sessionStorage.removeItem(AUTH_RETURN_KEY);
  return response.json() as Promise<T>;
}

export function reportParams(filters: Filters): Record<string, string> {
  return {
    period_from: filters.period_from,
    period_to: filters.period_to,
    sales_channel: filters.sales_channel,
    attribution_model: filters.attribution_model,
  };
}

export const api = {
  config: () => request<{ shops: Shop[] }>("/dashboard/config"),
  overview: (filters: Filters) =>
    request<Overview>("/api/v1/analytics/overview", reportParams(filters)),
  daily: (filters: Filters) =>
    request<DailyResponse>("/api/v1/analytics/overview/daily", reportParams(filters)),
  funnel: (filters: Filters) =>
    request<FunnelResponse>("/api/v1/analytics/funnel", reportParams(filters)),
  sources: (filters: Filters) =>
    request<SourcesResponse>("/api/v1/analytics/sources", reportParams(filters)),
  channels: (filters: Filters) =>
    request<ChannelsResponse>("/api/v1/analytics/contact-channels", reportParams(filters)),
  products: (filters: Filters) =>
    request<ProductsResponse>("/api/v1/analytics/products", reportParams(filters)),
  payments: (filters: Filters) =>
    request<PaymentsResponse>("/api/v1/analytics/payment-methods", reportParams(filters)),
  compare: (filters: Filters, compareFrom: string, compareTo: string) =>
    request<PeriodComparison>("/api/v1/analytics/period-comparison", {
      ...reportParams(filters),
      compare_from: compareFrom,
      compare_to: compareTo,
    }),
  searchJourney: (q: string) =>
    request<JourneySearchResponse>("/api/v1/analytics/journey/search", { q }),
  visitorJourney: (id: string) =>
    request<JourneyResponse>(`/api/v1/analytics/visitors/${id}/journey`),
  leadJourney: (id: string) =>
    request<JourneyResponse>(`/api/v1/analytics/leads/${id}/journey`),
  orderJourney: (id: string) =>
    request<JourneyResponse>(`/api/v1/analytics/orders/${id}/journey`),
  customerJourney: (id: string) =>
    request<JourneyResponse>(`/api/v1/analytics/customers/${id}/journey`),
};
