import { FormEvent, useState } from "react";
import { api } from "../api";
import { previousPeriod, toInput } from "../filters";
import {
  formatChangePct,
  formatDays,
  formatInt,
  formatMoney,
  formatMoneyList,
  formatPp,
  formatRate,
  formatSignedInt,
  PAYMENT_LABELS,
  tone,
} from "../format";
import { Panel } from "../states";
import type { Change, Filters, IntChange, PaymentRow, Shop } from "../types";
import { useApi } from "../useApi";

function Cell({
  now,
  was,
  delta,
}: {
  now: string;
  was: string;
  delta: { text: string; cls: string };
}) {
  return (
    <td>
      <div className="pair-now">{now}</div>
      <div className="pair-was">было {was}</div>
      <div className={`pair-delta ${delta.cls}`}>{delta.text}</div>
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
          <legend>Период 1</legend>
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
          <legend>Период 2</legend>
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
            <option value="last_non_direct">Last Non-Direct</option>
            <option value="first_touch">First Touch</option>
          </select>
        </label>
        <button type="submit">Сравнить</button>
      </form>
      <Panel loading={loading} error={error} empty={!current || !previous || !delta}>
        {current && previous && delta ? (
          <>
            <section className="card">
              <h2>Основные показатели</h2>
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Показатель</th>
                    <th>Значение</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Посетители</td>
                    <Cell
                      now={formatInt(current.visitors)}
                      was={formatInt(previous.visitors)}
                      delta={intDelta(delta.visitors)}
                    />
                  </tr>
                  <tr>
                    <td>Сессии</td>
                    <Cell
                      now={formatInt(current.sessions)}
                      was={formatInt(previous.sessions)}
                      delta={intDelta(delta.sessions)}
                    />
                  </tr>
                  <tr>
                    <td>Лиды</td>
                    <Cell
                      now={formatInt(current.leads)}
                      was={formatInt(previous.leads)}
                      delta={intDelta(delta.leads)}
                    />
                  </tr>
                  <tr>
                    <td>Оплаченные заказы</td>
                    <Cell
                      now={formatInt(current.orders_paid)}
                      was={formatInt(previous.orders_paid)}
                      delta={intDelta(delta.orders_paid)}
                    />
                  </tr>
                  <tr>
                    <td>Ручные продажи</td>
                    <Cell
                      now={formatInt(current.manual_sales)}
                      was={formatInt(previous.manual_sales)}
                      delta={intDelta(delta.manual_sales)}
                    />
                  </tr>
                  {delta.money.map((row) => (
                    <tr key={row.currency}>
                      <td>Выручка без возвратов ({row.currency})</td>
                      <Cell
                        now={formatMoney(
                          current.money.find((item) => item.currency === row.currency)
                            ?.net,
                          row.currency,
                        )}
                        was={formatMoney(
                          previous.money.find((item) => item.currency === row.currency)
                            ?.net,
                          row.currency,
                        )}
                        delta={moneyDelta(row.net.abs, row.net.pct, row.currency)}
                      />
                    </tr>
                  ))}
                  <tr>
                    <td>Сессия → лид</td>
                    <Cell
                      now={formatRate(current.session_to_lead)}
                      was={formatRate(previous.session_to_lead)}
                      delta={rateDelta(delta.session_to_lead)}
                    />
                  </tr>
                  <tr>
                    <td>Лид → продажа</td>
                    <Cell
                      now={formatRate(current.lead_to_paid_sale)}
                      was={formatRate(previous.lead_to_paid_sale)}
                      delta={rateDelta(delta.lead_to_paid_sale)}
                    />
                  </tr>
                  <tr>
                    <td>Время до продажи</td>
                    <Cell
                      now={formatDays(current.first_visit_to_paid_sale_seconds)}
                      was={formatDays(previous.first_visit_to_paid_sale_seconds)}
                      delta={daysDelta(delta.first_visit_to_paid_sale_seconds)}
                    />
                  </tr>
                </tbody>
              </table>
            </section>
            {methods?.delta.length ? (
              <section className="card">
                <h2>Способы оплаты</h2>
                <p className="hint">
                  Одна строка — один метод. В ячейке: сейчас, было, разница. Конверсии — в
                  пунктах (п.п.).
                </p>
                <table className="compare-table">
                  <thead>
                    <tr>
                      <th>Способ</th>
                      <th>Показан на checkout</th>
                      <th>Доля выбора</th>
                      <th>Ошибки оплаты</th>
                      <th>Выбрали и оплатили</th>
                      <th>Выручка без возвратов</th>
                    </tr>
                  </thead>
                  <tbody>
                    {methods.delta.map((row) => {
                      const now = findMethod(methods.current, row.payment_method);
                      const then = findMethod(methods.previous, row.payment_method);
                      return (
                        <tr key={row.payment_method}>
                          <td>
                            {PAYMENT_LABELS[row.payment_method] ?? row.payment_method}
                          </td>
                          <Cell
                            now={formatInt(now?.shown ?? 0)}
                            was={formatInt(then?.shown ?? 0)}
                            delta={intDelta(row.shown)}
                          />
                          <Cell
                            now={formatRate(now?.selected_rate)}
                            was={formatRate(then?.selected_rate)}
                            delta={rateDelta(row.selected_rate)}
                          />
                          <Cell
                            now={formatInt(now?.failed ?? 0)}
                            was={formatInt(then?.failed ?? 0)}
                            delta={intDelta(row.failed)}
                          />
                          <Cell
                            now={formatRate(now?.selected_to_paid)}
                            was={formatRate(then?.selected_to_paid)}
                            delta={rateDelta(row.selected_to_paid)}
                          />
                          <Cell
                            now={formatMoneyList(now?.money ?? [], "net")}
                            was={formatMoneyList(then?.money ?? [], "net")}
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
