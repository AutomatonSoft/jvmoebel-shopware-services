import { api } from "../api";
import { CHANNEL_LABELS, formatDays, formatInt, formatMoneyList, formatRate } from "../format";
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
        Кампании по модели атрибуции из фильтра: Visitors, Leads, Sales, conversion,
        revenue, средний чек и время до Sale.
      </p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Campaign</th>
                <th>Visitors</th>
                <th>Leads</th>
                <th>Sales</th>
                <th>Conv.</th>
                <th>Revenue</th>
                <th>AOV</th>
                <th>До Sale</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={`${row.source}:${row.campaign ?? ""}`}>
                  <td>{row.source}</td>
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
      <p className="lead">Сравнение form / email / WhatsApp / phone.</p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Канал</th>
                <th>Intents</th>
                <th>Contacts</th>
                <th>Leads</th>
                <th>Sales</th>
                <th>Contact → Lead</th>
                <th>Lead → Sale</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.channel}>
                  <td>{CHANNEL_LABELS[row.channel] ?? row.channel}</td>
                  <td>{formatInt(row.intents)}</td>
                  <td>{formatInt(row.contacts)}</td>
                  <td>{formatInt(row.leads)}</td>
                  <td>{formatInt(row.orders_paid + row.manual_sales)}</td>
                  <td>{formatRate(row.contact_to_lead)}</td>
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
      <p className="lead">SKU: просмотры, корзина, покупки, conversion и revenue.</p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Views</th>
                <th>Add to cart</th>
                <th>Purchases</th>
                <th>Conversion</th>
                <th>Revenue</th>
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
      <p className="lead">Доступность, выбор, ошибки, успешные оплаты, conversion и средний чек.</p>
      <Panel loading={loading} error={error} empty={items.length === 0}>
        <section className="card">
          <table>
            <thead>
              <tr>
                <th>Метод</th>
                <th>Shown</th>
                <th>Selected</th>
                <th>Errors</th>
                <th>Paid</th>
                <th>Select rate</th>
                <th>Selected → Paid</th>
                <th>Revenue</th>
                <th>AOV</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.payment_method}>
                  <td>{row.payment_method}</td>
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
