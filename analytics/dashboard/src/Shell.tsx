import { FormEvent } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { toInput } from "./filters";
import type { Filters, Shop } from "./types";

const NAV = [
  ["/", "Обзор"],
  ["/sources", "Источники"],
  ["/channels", "Каналы"],
  ["/products", "Товары"],
  ["/payments", "Оплата"],
  ["/compare", "Сравнение"],
  ["/journey", "Путь клиента"],
] as const;

type Props = {
  filters: Filters;
  shops: Shop[];
  onChange: (next: Filters) => void;
};

export function Shell({ filters, shops, onChange }: Props) {
  const isCompare = useLocation().pathname === "/compare";
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const from = String(data.get("period_from"));
    const to = String(data.get("period_to"));
    onChange({
      period_from: `${from}:00Z`,
      period_to: `${to}:59Z`,
      sales_channel: String(data.get("sales_channel") ?? ""),
      attribution_model:
        data.get("attribution_model") === "first_touch"
          ? "first_touch"
          : "last_non_direct",
    });
  }

  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          JV Möbel Analytics
          <span>Закрытый дашборд</span>
        </div>
        {NAV.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            {label}
          </NavLink>
        ))}
      </aside>
      <main className="main">
        {isCompare ? null : (
          <>
            <form className="filters" onSubmit={submit}>
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
              <button type="submit">Показать</button>
            </form>
            <p className="lead">
              Фильтры: {filters.period_from.replace("T", " ").replace("Z", " UTC")} —{" "}
              {filters.period_to.replace("T", " ").replace("Z", " UTC")} ·{" "}
              {shops.find((shop) => shop.id === filters.sales_channel)?.label ??
                "все магазины"}{" "}
              ·{" "}
              {filters.attribution_model === "first_touch"
                ? "First Touch"
                : "Last Non-Direct Touch"}
            </p>
          </>
        )}
        <Outlet />
      </main>
    </div>
  );
}
