import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { api } from "../api";
import {
  formatDays,
  formatInt,
  formatMoneyList,
  formatRate,
  FUNNEL_LABELS,
} from "../format";
import { Panel } from "../states";
import type { Filters, FunnelStep } from "../types";
import { useApi } from "../useApi";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FunnelCard({
  title,
  steps,
  showRates,
}: {
  title: string;
  steps: FunnelStep[];
  showRates: boolean;
}) {
  const max = Math.max(1, ...steps.map((step) => step.count));
  return (
    <section className="card">
      <h2>{title}</h2>
      <p className="hint">Количество за период</p>
      <div className="funnel">
        {steps.map((step) => (
          <div className="funnel-row" key={step.key}>
            <span>{FUNNEL_LABELS[step.key] ?? step.key}</span>
            <div className="bar">
              <i style={{ width: `${(step.count / max) * 100}%` }} />
            </div>
            <strong>
              {formatInt(step.count)}
              {showRates && step.conversion_from_previous
                ? ` · ${formatRate(step.conversion_from_previous)}`
                : ""}
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function OverviewPage({ filters }: { filters: Filters }) {
  const overview = useApi(() => api.overview(filters), [filters]);
  const funnel = useApi(() => api.funnel(filters), [filters]);
  const daily = useApi(() => api.daily(filters), [filters]);
  const data = overview.data;
  const points = daily.data?.items ?? [];
  const revenue = points.map((point) => Number(point.money[0]?.net ?? 0));

  return (
    <>
      <h1>Обзор</h1>
      <p className="lead">KPI, воронки и динамика оплаченных продаж за выбранный период.</p>
      <Panel loading={overview.loading} error={overview.error} empty={false}>
        {data ? (
          <div className="kpis">
            <Kpi label="Посетители" value={formatInt(data.visitors)} />
            <Kpi label="Сессии" value={formatInt(data.sessions)} />
            <Kpi label="Лиды" value={formatInt(data.leads)} />
            <Kpi
              label="Оплаченные продажи"
              value={formatInt(data.orders_paid + data.manual_sales)}
            />
            <Kpi
              label="Выручка (без возвратов)"
              value={formatMoneyList(data.money, "net")}
            />
            <Kpi
              label="Средний чек (до возвратов)"
              value={formatMoneyList(data.money, "aov")}
            />
            <Kpi label="Сессия → лид" value={formatRate(data.session_to_lead)} />
            <Kpi label="Лид → продажа" value={formatRate(data.lead_to_paid_sale)} />
            <Kpi
              label="До продажи"
              value={formatDays(data.first_visit_to_paid_sale_seconds)}
            />
          </div>
        ) : null}
      </Panel>
      <Panel loading={funnel.loading} error={funnel.error} empty={false}>
        {funnel.data ? (
          <div className="grid-2">
            <FunnelCard title="Ecommerce-воронка" steps={funnel.data.ecommerce} showRates />
            <FunnelCard title="Lead-воронка" steps={funnel.data.lead} showRates={false} />
          </div>
        ) : null}
      </Panel>
      <section className="card">
        <h2>Оплаченные продажи и выручка</h2>
        <Panel loading={daily.loading} error={daily.error} empty={points.length === 0}>
          <Line
            data={{
              labels: points.map((point) => point.date),
              datasets: [
                {
                  label: "Оплаченные продажи",
                  data: points.map((point) => point.paid_sales),
                  borderColor: "#215c3a",
                  backgroundColor: "#215c3a",
                  yAxisID: "y",
                  tension: 0.2,
                },
                {
                  label: "Выручка (без возвратов)",
                  data: revenue,
                  borderColor: "#c46a2b",
                  backgroundColor: "#c46a2b",
                  yAxisID: "y1",
                  tension: 0.2,
                },
              ],
            }}
            options={{
              responsive: true,
              interaction: { mode: "index", intersect: false },
              plugins: { legend: { position: "bottom" } },
              scales: {
                y: { beginAtZero: true, title: { display: true, text: "Продажи" } },
                y1: {
                  beginAtZero: true,
                  position: "right",
                  grid: { drawOnChartArea: false },
                  title: { display: true, text: "Выручка" },
                },
              },
            }}
          />
        </Panel>
      </section>
    </>
  );
}
