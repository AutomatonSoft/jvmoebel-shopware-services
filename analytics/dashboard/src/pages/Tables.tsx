import { api } from "../api";
import {
  CHANNEL_LABELS,
  formatDays,
  formatInt,
  formatMoneyList,
  formatRate,
  labelPayment,
  labelSource,
} from "../format";
import { Panel } from "../states";
import type { Filters } from "../types";
import { useApi } from "../useApi";

export function SourcesPage({ filters }: { filters: Filters }) {
  const { data, loading, error } = useApi(() => api.sources(filters), [filters]);
  const items = data?.items ?? [];

  return (
    <>
      <h1>Источники</h1>
      <p className="lead">
        Кампании по модели атрибуции из фильтра: посетители, лиды, продажи, конверсия,
        выручка без возвратов, средний чек до возвратов и время до продажи.
      </p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Источник</th>
                <th>Кампания</th>
                <th>Посетители</th>
                <th>Лиды</th>
                <th>Продажи</th>
                <th>Конверсия</th>
                <th>Выручка (без возвратов)</th>
                <th>Средний чек (до возвратов)</th>
                <th>До продажи</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={`${row.source}:${row.campaign ?? ""}`}>
                  <td>{labelSource(row.source)}</td>
                  <td>{row.campaign ?? "—"}</td>
                  <td>{formatInt(row.visitors)}</td>
                  <td>{formatInt(row.leads)}</td>
                  <td>{formatInt(row.orders_paid + row.manual_sales)}</td>
                  <td>{formatRate(row.session_to_paid_sale)}</td>
                  <td>{formatMoneyList(row.money, "net")}</td>
                  <td>{formatMoneyList(row.money, "aov")}</td>
                  <td>{formatDays(row.first_visit_to_paid_sale_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </Panel>
    </>
  );
}

export function ChannelsPage({ filters }: { filters: Filters }) {
  const { data, loading, error } = useApi(() => api.channels(filters), [filters]);
  const items = data?.items ?? [];

  return (
    <>
      <h1>Каналы обращений</h1>
      <p className="lead">
        Сравнение form / email / WhatsApp / phone. Конверсия обращение → лид и лид → продажа
        за период.
      </p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Канал</th>
                <th>Нажатия «написать»</th>
                <th>Обращения</th>
                <th>Лиды</th>
                <th>Обращение → лид</th>
                <th>Продажи</th>
                <th>Лид → продажа</th>
                <th>Выручка (без возвратов)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.channel}>
                  <td>{CHANNEL_LABELS[row.channel] ?? row.channel}</td>
                  <td>{formatInt(row.intents)}</td>
                  <td>{formatInt(row.contacts)}</td>
                  <td>{formatInt(row.leads)}</td>
                  <td>{formatRate(row.contact_to_lead)}</td>
                  <td>{formatInt(row.orders_paid + row.manual_sales)}</td>
                  <td>{formatRate(row.lead_to_paid_sale)}</td>
                  <td>{formatMoneyList(row.money, "net")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </Panel>
    </>
  );
}

export function ProductsPage({ filters }: { filters: Filters }) {
  const { data, loading, error } = useApi(() => api.products(filters), [filters]);
  const items = data?.items ?? [];

  return (
    <>
      <h1>Товары</h1>
      <p className="lead">Артикул: просмотры, корзина, покупки, конверсия и выручка без возвратов.</p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Артикул</th>
                <th>Просмотры</th>
                <th>В корзину</th>
                <th>Покупки</th>
                <th>Конверсия</th>
                <th>Выручка (без возвратов)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.sku}>
                  <td>{row.sku}</td>
                  <td>{formatInt(row.views)}</td>
                  <td>{formatInt(row.cart_adds)}</td>
                  <td>{formatInt(row.orders_paid)}</td>
                  <td>{formatRate(row.view_to_paid_order)}</td>
                  <td>{formatMoneyList(row.money, "net")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </Panel>
    </>
  );
}

export function PaymentsPage({ filters }: { filters: Filters }) {
  const { data, loading, error } = useApi(() => api.payments(filters), [filters]);
  const items = data?.items ?? [];

  return (
    <>
      <h1>Способы оплаты</h1>
      <p className="lead">
        Доступность, выбор, ошибки, успешные оплаты, конверсия и средний чек до возвратов.
      </p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Способ</th>
                <th>Показан</th>
                <th>Выбран</th>
                <th>Ошибки</th>
                <th>Оплачен</th>
                <th>Доля выбора</th>
                <th>Выбрали и оплатили</th>
                <th>Выручка (без возвратов)</th>
                <th>Средний чек (до возвратов)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.payment_method}>
                  <td>{labelPayment(row.payment_method)}</td>
                  <td>{formatInt(row.shown)}</td>
                  <td>{formatInt(row.selected)}</td>
                  <td>{formatInt(row.failed)}</td>
                  <td>{formatInt(row.orders_paid)}</td>
                  <td>{formatRate(row.selected_rate)}</td>
                  <td>{formatRate(row.selected_to_paid)}</td>
                  <td>{formatMoneyList(row.money, "net")}</td>
                  <td>{formatMoneyList(row.money, "aov")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </Panel>
    </>
  );
}
