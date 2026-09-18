import type { Filters } from "./types";

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function utcStamp(date: Date, end = false): string {
  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  return end
    ? `${year}-${month}-${day}T23:59:59Z`
    : `${year}-${month}-${day}T00:00:00Z`;
}

export function defaultFilters(): Filters {
  const now = new Date();
  const from = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - 6),
  );
  return {
    period_from: utcStamp(from),
    period_to: utcStamp(now, true),
    sales_channel: "",
    attribution_model: "last_non_direct",
  };
}

export function previousPeriod(filters: Filters): { from: string; to: string } {
  const fromMs = Date.parse(filters.period_from);
  const toMs = Date.parse(filters.period_to);
  const length = Math.max(toMs - fromMs, 0);
  const prevTo = new Date(fromMs - 1000);
  const prevFrom = new Date(prevTo.getTime() - length);
  return {
    from: prevFrom.toISOString().replace(/\.\d{3}Z$/, "Z"),
    to: prevTo.toISOString().replace(/\.\d{3}Z$/, "Z"),
  };
}

export function toInput(iso: string): string {
  return iso.slice(0, 16);
}
