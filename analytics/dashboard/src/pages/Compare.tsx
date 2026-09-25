import { FormEvent, useState } from "react";
import { api } from "../api";
import { previousPeriod, toInput } from "../filters";
import {
  ATTRIBUTION_LABELS,
  formatChangePct,
  formatDays,
  formatInt,
  formatMoney,
  formatMoneyList,
  formatPp,
  formatRate,
  formatSignedInt,
  labelPayment,
  tone,
} from "../format";
import { Panel } from "../states";
import type { Change, Filters, IntChange, PaymentRow, Shop } from "../types";
import { useApi } from "../useApi";

function Flow({ period1, period2 }: { period1: string; period2: string }) {
  return (
    <span className="flow">
      {period2}
      <span className="flow-arrow">→</span>
      {period1}
    </span>
  );
}

function MetricRow({
  label,
  period1,
  period2,
  delta,
}: {
  label: string;
  period1: string;
  period2: string;
  delta: { text: string; cls: string };
}) {
  return (
    <tr>
      <td>{label}</td>
      <td>
        <Flow period1={period1} period2={period2} />
      </td>
      <td className={delta.cls}>{delta.text}</td>
    </tr>
  );
}

function PairCell({
  period1,
  period2,
  delta,
}: {
  period1: string;
  period2: string;
  delta: { text: string; cls: string };
}) {
  return (
    <td>
      <div className="pair">
        <Flow period1={period1} period2={period2} />
        <span className={delta.cls}>{delta.text}</span>
      </div>
    </td>
  );
}

function intDelta(change: IntChange): { text: string; cls: string } {
  const pct = change.pct == null ? "" : ` (${formatChangePct(change.pct)})`;
  return {
    text: `${formatSignedInt(change.abs)}${pct}`,
    cls: tone(change.abs),
  };
}

function rateDelta(change: Change): { text: string; cls: string } {
  return { text: formatPp(change.abs), cls: tone(change.abs) };
}

function daysDelta(change: Change): { text: string; cls: string } {
  const pct = change.pct == null ? "" : ` (${formatChangePct(change.pct)})`;
  return {
    text: `${change.abs == null ? "—" : formatDays(change.abs)}${pct}`,
    cls: tone(change.abs),
  };
}

function moneyDelta(abs: string | null, pct: string | null, currency: string) {
  const signed =
    abs == null ? "—" : `${Number(abs) > 0 ? "+" : ""}${formatMoney(abs, currency)}`;
  const relative = pct == null ? "" : ` (${formatChangePct(pct)})`;
  return { text: `${signed}${relative}`, cls: tone(abs) };
}

function findMethod(rows: PaymentRow[], method: string): PaymentRow | undefined {
  return rows.find((row) => row.payment_method === method);
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
  const methods = data?.payment_methods;

  return (
    <>
      <h1>Сравнение периодов</h1>
      <p className="note">
        Сопоставление двух интервалов, а не доказательство причины.
      </p>
      <form className="filters compare-form" onSubmit={submit}>
        <fieldset>
          <legend>Стало</legend>
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
        </fieldset>
        <fieldset>
          <legend>Было</legend>
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
        </fieldset>
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
            <option value="last_non_direct">
              {ATTRIBUTION_LABELS.last_non_direct}
            </option>
            <option value="first_touch">{ATTRIBUTION_LABELS.first_touch}</option>
          </select>
        </label>
        <button type="submit">Сравнить</button>
      </form>
      <Panel loading={loading} error={error} empty={!current || !previous || !delta}>
        {current && previous && delta ? (
          <>
            <section className="card">
              <h2>Основные показатели</h2>
              <table className="compare-table compare-metrics">
                <thead>
                  <tr>
                    <th>Показатель</th>
                    <th>Было → Стало</th>
                    <th>Разница</th>
                  </tr>
                </thead>
                <tbody>
                  <MetricRow
                    label="Посетители"
                    period1={formatInt(current.visitors)}
                    period2={formatInt(previous.visitors)}
                    delta={intDelta(delta.visitors)}
                  />
                  <MetricRow
                    label="Сессии"
                    period1={formatInt(current.sessions)}
                    period2={formatInt(previous.sessions)}
                    delta={intDelta(delta.sessions)}
                  />
                  <MetricRow
                    label="Лиды"
                    period1={formatInt(current.leads)}
                    period2={formatInt(previous.leads)}
                    delta={intDelta(delta.leads)}
                  />
                  <MetricRow
                    label="Оплаченные заказы"
                    period1={formatInt(current.orders_paid)}
                    period2={formatInt(previous.orders_paid)}
                    delta={intDelta(delta.orders_paid)}
                  />
                  <MetricRow
                    label="Ручные продажи"
                    period1={formatInt(current.manual_sales)}
                    period2={formatInt(previous.manual_sales)}
                    delta={intDelta(delta.manual_sales)}
                  />
                  {delta.money.map((row) => (
                    <MetricRow
                      key={row.currency}
                      label={`Выручка (без возвратов), ${row.currency}`}
                      period1={formatMoney(
                        current.money.find((item) => item.currency === row.currency)?.net,
                        row.currency,
                      )}
                      period2={formatMoney(
                        previous.money.find((item) => item.currency === row.currency)
                          ?.net,
                        row.currency,
                      )}
                      delta={moneyDelta(row.net.abs, row.net.pct, row.currency)}
                    />
                  ))}
                  <MetricRow
                    label="Сессия → лид"
                    period1={formatRate(current.session_to_lead)}
                    period2={formatRate(previous.session_to_lead)}
                    delta={rateDelta(delta.session_to_lead)}
                  />
                  <MetricRow
                    label="Лид → продажа"
                    period1={formatRate(current.lead_to_paid_sale)}
                    period2={formatRate(previous.lead_to_paid_sale)}
                    delta={rateDelta(delta.lead_to_paid_sale)}
                  />
                  <MetricRow
                    label="Время до продажи"
                    period1={formatDays(current.first_visit_to_paid_sale_seconds)}
                    period2={formatDays(previous.first_visit_to_paid_sale_seconds)}
                    delta={daysDelta(delta.first_visit_to_paid_sale_seconds)}
                  />
                </tbody>
              </table>
            </section>
            {methods?.delta.length ? (
              <section className="card">
                <h2>Способы оплаты</h2>
                <table className="compare-table">
                  <thead>
                    <tr>
                      <th>Способ</th>
                      <th>Показан на checkout</th>
                      <th>Доля выбора</th>
                      <th>Ошибки оплаты</th>
                      <th>Выбрали и оплатили</th>
                      <th>Выручка (без возвратов)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {methods.delta.map((row) => {
                      const now = findMethod(methods.current, row.payment_method);
                      const then = findMethod(methods.previous, row.payment_method);
                      return (
                        <tr key={row.payment_method}>
                          <td>
                            {labelPayment(row.payment_method)}
                          </td>
                          <PairCell
                            period1={formatInt(now?.shown ?? 0)}
                            period2={formatInt(then?.shown ?? 0)}
                            delta={intDelta(row.shown)}
                          />
                          <PairCell
                            period1={formatRate(now?.selected_rate)}
                            period2={formatRate(then?.selected_rate)}
                            delta={rateDelta(row.selected_rate)}
                          />
                          <PairCell
                            period1={formatInt(now?.failed ?? 0)}
                            period2={formatInt(then?.failed ?? 0)}
                            delta={intDelta(row.failed)}
                          />
                          <PairCell
                            period1={formatRate(now?.selected_to_paid)}
                            period2={formatRate(then?.selected_to_paid)}
                            delta={rateDelta(row.selected_to_paid)}
                          />
                          <PairCell
                            period1={formatMoneyList(now?.money ?? [], "net")}
                            period2={formatMoneyList(then?.money ?? [], "net")}
                            delta={
                              row.money[0]
                                ? moneyDelta(
                                    row.money[0].net.abs,
                                    row.money[0].net.pct,
                                    row.money[0].currency,
                                  )
                                : { text: "—", cls: "" }
                            }
                          />
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </section>
            ) : null}
          </>
        ) : null}
      </Panel>
    </>
  );
}
