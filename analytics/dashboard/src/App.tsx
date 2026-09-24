import { useEffect, useState, type ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useSearchParams,
} from "react-router-dom";
import { api, safeDashboardNext } from "./api";
import { defaultFilters } from "./filters";
import { ComparePage } from "./pages/Compare";
import { JourneyPage } from "./pages/Journey";
import { OverviewPage } from "./pages/Overview";
import {
  ChannelsPage,
  PaymentsPage,
  ProductsPage,
  SourcesPage,
} from "./pages/Tables";
import { Shell } from "./Shell";
import type { Filters, Shop } from "./types";

function RestorePath({ children }: { children: ReactNode }) {
  const [params] = useSearchParams();
  const next = safeDashboardNext(params.get("next"));
  if (next) return <Navigate to={next} replace />;
  return children;
}

export function App() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [shops, setShops] = useState<Shop[]>([]);

  useEffect(() => {
    api
      .config()
      .then((config) => setShops(config.shops))
      .catch(() => setShops([]));
  }, []);

  return (
    <BrowserRouter basename="/dashboard">
      <Routes>
        <Route
          element={
            <RestorePath>
              <Shell filters={filters} shops={shops} onChange={setFilters} />
            </RestorePath>
          }
        >
          <Route path="/" element={<OverviewPage filters={filters} />} />
          <Route path="/funnel" element={<Navigate to="/" replace />} />
          <Route path="/sources" element={<SourcesPage filters={filters} />} />
          <Route path="/channels" element={<ChannelsPage filters={filters} />} />
          <Route path="/products" element={<ProductsPage filters={filters} />} />
          <Route path="/payments" element={<PaymentsPage filters={filters} />} />
          <Route
            path="/compare"
            element={
              <ComparePage filters={filters} shops={shops} onChange={setFilters} />
            }
          />
          <Route path="/journey" element={<JourneyPage shops={shops} />} />
          <Route
            path="/journey/:entity/:id"
            element={<JourneyPage shops={shops} />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
