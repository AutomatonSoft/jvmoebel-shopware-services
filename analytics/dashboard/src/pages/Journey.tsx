import { FormEvent, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import {
  ENTITY_LABELS,
  EVENT_LABELS,
  formatDateTime,
  shopName,
  summarizeJourneyEvent,
} from "../format";
import { Panel } from "../states";
import type { JourneyEvent, JourneyHit, Shop } from "../types";
import { useApi } from "../useApi";

const DETAIL: Record<string, (id: string) => Promise<{ events: JourneyEvent[] }>> = {
  visitor: api.visitorJourney,
  lead: api.leadJourney,
  order: api.orderJourney,
  customer: api.customerJourney,
};

function Timeline({ events }: { events: JourneyEvent[] }) {
  if (!events.length) return <div className="state">Событий нет</div>;
  return (
    <ol className="timeline">
      {events.map((event) => {
        const summary = summarizeJourneyEvent(
          event.payload,
          event.event_type,
          event.traffic_source,
        );
        return (
          <li key={event.event_id}>
            <time>{formatDateTime(event.occurred_at)}</time>
            <strong>{EVENT_LABELS[event.event_type] ?? event.event_type}</strong>
            {summary ? <p>{summary}</p> : null}
            <details>
              <summary>JSON</summary>
              <pre>{JSON.stringify(event.payload, null, 2)}</pre>
            </details>
          </li>
        );
      })}
    </ol>
  );
}

export function JourneyPage({ shops }: { shops: Shop[] }) {
  const { entity, id } = useParams();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") ?? "");

  const search = useApi(
    () => (query ? api.searchJourney(query) : Promise.resolve({ items: [] as JourneyHit[] })),
    [query],
  );
  const detailLoader = entity && id && DETAIL[entity];
  const detail = useApi(
    () => (detailLoader && id ? detailLoader(id) : Promise.resolve({ events: [] })),
    [entity, id],
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    setQuery(next);
    setParams(next ? { q: next } : {});
  }

  const hits = search.data?.items ?? [];
  const unsupported = Boolean(entity && id && !DETAIL[entity ?? ""]);

  return (
    <>
      <h1>Путь клиента</h1>
      <p className="lead">
        Поиск по Order ID/Number, Lead ID, Visitor ID, Customer ID, GCLID/GBRAID/WBRAID,
        campaign, каналу или tracking reference.
      </p>
      <form className="search" onSubmit={submit}>
        <input
          name="q"
          defaultValue={query}
          key={query}
          placeholder="DEV-00-000, UUID, campaign…"
        />
        <button type="submit">Найти</button>
      </form>
      {unsupported ? (
        <p className="note">
          Лента событий открывается для Visitor, Lead, Order и Customer. Для сессии или
          обращения найдите связанный Visitor/Lead.
        </p>
      ) : null}
      {entity && id && DETAIL[entity] ? (
        <section className="card">
          <h2>
            {ENTITY_LABELS[entity] ?? entity}: {id}
          </h2>
          <Panel loading={detail.loading} error={detail.error} empty={false}>
            <Timeline events={detail.data?.events ?? []} />
          </Panel>
        </section>
      ) : null}
      <Panel
        loading={Boolean(query) && search.loading}
        error={search.error}
        empty={Boolean(query) && !search.loading && hits.length === 0}
      >
        {hits.length ? (
          <section className="card">
            <table>
              <thead>
                <tr>
                  <th>Тип</th>
                  <th>ID</th>
                  <th>Магазин</th>
                  <th>Время</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {hits.map((hit) => (
                  <tr key={`${hit.entity_type}:${hit.id}`}>
                    <td>{ENTITY_LABELS[hit.entity_type] ?? hit.entity_type}</td>
                    <td>{hit.id}</td>
                    <td>{shopName(shops, hit.sales_channel_id)}</td>
                    <td>{formatDateTime(hit.occurred_at)}</td>
                    <td>
                      {DETAIL[hit.entity_type] ? (
                        <Link to={`/journey/${hit.entity_type}/${hit.id}`}>Открыть</Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}
      </Panel>
    </>
  );
}
