import { FormEvent, useState } from "react";
import { api } from "../api";
import { previousPeriod, toInput } from "../filters";
import {
  formatChangePct,
  formatDays,
  formatInt,
  formatMoney,
  formatRate,
  formatSignedInt,
  tone,
} from "../format";
import { Panel } from "../states";
import type { Change, Filters, IntChange, Shop } from "../types";
import { useApi } from "../useApi";

function Metric({
  label,
  current,
  previous,
  delta,
}: {
  label: string;
  current: string;
  previous: string;
  delta: { text: string; cls: string };
}) {
  return (
    <tr>
      <td>{label}</td>
      <td>{current}</td>
      <td>{previous}</td>
      <td className={delta.cls}>{delta.text}</td>
    </tr>
  );
}

function intDelta(change: IntChange): { text: string; cls: string } {
  return {
    text: `${formatSignedInt(change.abs)} · ${formatChangePct(change.pct)}`,
    cls: tone(change.abs),
  };
}

function rateDelta(change: Change): { text: string; cls: string } {
  return {
    text: `${change.abs == null ? "—" : formatRate(change.abs)} · ${formatChangePct(change.pct)}`,
    cls: tone(change.abs),
  };
}

function daysDelta(change: Change): { text: string; cls: string } {
  return {
    text: `${formatDays(change.abs)} · ${formatChangePct(change.pct)}`,
    cls: tone(change.abs),
  };
}

function moneyDelta(abs: string | null, pct: string | null, currency: string) {
  const signed = abs == null ? "—" : `${Number(abs) > 0 ? "+" : ""}${formatMoney(abs, currency)}`;
  return {
    text: `${signed} · ${formatChangePct(pct)}`,
    cls: tone(abs),
  };
}

export function ComparePage({
  filters,
  shops,
  onChange,
}: {
  filters: Filters;
  shops: Shop[];
  onChange: (next: Filters) => void;
}) {
  const [compareFrom, setCompareFrom] = useState(() => previousPeriod(filters).from);
  const [compareTo, setCompareTo] = useState(() => previousPeriod(filters).to);

  const { data, loading, error } = useApi(
    () => api.compare(filters, compareFrom, compareTo),
    [filters, compareFrom, compareTo],
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onChange({
      period_from: `${String(form.get("period_from"))}:00Z`,
      period_to: `${String(form.get("period_to"))}:59Z`,
      sales_channel: String(form.get("sales_channel") ?? ""),
      attribution_model:
        form.get("attribution_model") === "first_touch"
          ? "first_touch"
          : "last_non_direct",
    });
    setCompareFrom(`${String(form.get("compare_from"))}:00Z`);
    setCompareTo(`${String(form.get("compare_to"))}:59Z`);
  }

  const current = data?.current;
  const previous = data?.previous;
  const delta = data?.delta;

  return (
    <>
      <h1>Сравнение периодов</h1>
      <p className="lead">Абсолютное и процентное изменение показателей.</p>
      <form onSubmit={submit}>
        <div className="filters">
          <strong className="period-name">Период 1</strong>
          <label>
            С
            <input
              type="datetime-local"
              name="period_from"
              defaultValue={toInput(filters.period_from)}
              key={filters.period_from}
            />
          </label>
          <label>
            По
            <input
              type="datetime-local"
              name="period_to"
              defaultValue={toInput(filters.period_to)}
              key={filters.period_to}
            />
          </label>
        </div>
        <div className="filters">
          <strong className="period-name">Период 2</strong>
          <label>
            С
            <input
              type="datetime-local"
              name="compare_from"
              defaultValue={toInput(compareFrom)}
              key={compareFrom}
            />
          </label>
          <label>
            По
            <input
              type="datetime-local"
              name="compare_to"
              defaultValue={toInput(compareTo)}
              key={compareTo}
            />
          </label>
        </div>
        <div className="filters">
          <label>
            Магазин
            <select
              name="sales_channel"
              defaultValue={filters.sales_channel}
              key={filters.sales_channel}
            >
              <option value="">Все магазины</option>
              {shops.map((shop) => (
                <option key={shop.id} value={shop.id}>
                  {shop.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Атрибуция
            <select
              name="attribution_model"
              defaultValue={filters.attribution_model}
              key={filters.attribution_model}
            >
              <option value="last_non_direct">Last Non-Direct</option>
              <option value="first_touch">First Touch</option>
            </select>
          </label>
          <button type="submit">Сравнить</button>
        </div>
      </form>
      <Panel loading={loading} error={error} empty={!current || !previous || !delta}>
        {current && previous && delta ? (
          <section className="card">
            <table>
              <thead>
                <tr>
                  <th>Показатель</th>
                  <th>Период 1</th>
                  <th>Период 2</th>
                  <th>Δ / %</th>
                </tr>
              </thead>
              <tbody>
                <Metric
                  label="Visitors"
                  current={formatInt(current.visitors)}
                  previous={formatInt(previous.visitors)}
                  delta={intDelta(delta.visitors)}
                />
                <Metric
                  label="Sessions"
                  current={formatInt(current.sessions)}
                  previous={formatInt(previous.sessions)}
                  delta={intDelta(delta.sessions)}
                />
                <Metric
                  label="Leads"
                  current={formatInt(current.leads)}
                  previous={formatInt(previous.leads)}
                  delta={intDelta(delta.leads)}
                />
                <Metric
                  label="Orders paid"
                  current={formatInt(current.orders_paid)}
                  previous={formatInt(previous.orders_paid)}
                  delta={intDelta(delta.orders_paid)}
                />
                <Metric
                  label="Manual sales"
                  current={formatInt(current.manual_sales)}
                  previous={formatInt(previous.manual_sales)}
                  delta={intDelta(delta.manual_sales)}
                />
                {delta.money.map((row) => (
                  <Metric
                    key={row.currency}
                    label={`Revenue ${row.currency}`}
                    current={formatMoney(
                      current.money.find((item) => item.currency === row.currency)?.net,
                      row.currency,
                    )}
                    previous={formatMoney(
                      previous.money.find((item) => item.currency === row.currency)?.net,
                      row.currency,
                    )}
                    delta={moneyDelta(row.net.abs, row.net.pct, row.currency)}
                  />
                ))}
                <Metric
                  label="Session → Lead"
                  current={formatRate(current.session_to_lead)}
                  previous={formatRate(previous.session_to_lead)}
                  delta={rateDelta(delta.session_to_lead)}
                />
                <Metric
                  label="Lead → Sale"
                  current={formatRate(current.lead_to_paid_sale)}
                  previous={formatRate(previous.lead_to_paid_sale)}
                  delta={rateDelta(delta.lead_to_paid_sale)}
                />
                <Metric
                  label="До Sale"
                  current={formatDays(current.first_visit_to_paid_sale_seconds)}
                  previous={formatDays(previous.first_visit_to_paid_sale_seconds)}
                  delta={daysDelta(delta.first_visit_to_paid_sale_seconds)}
                />
              </tbody>
            </table>
          </section>
        ) : null}
      </Panel>
    </>
  );
}
