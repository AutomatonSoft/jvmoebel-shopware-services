import { ReactNode } from "react";

export function Loading() {
  return <div className="state">Загрузка…</div>;
}

export function Empty() {
  return <div className="state">Нет данных за период</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="state error">{message}</div>;
}

export function Panel({
  loading,
  error,
  empty,
  children,
}: {
  loading: boolean;
  error: string | null;
  empty: boolean;
  children: ReactNode;
}) {
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;
  if (empty) return <Empty />;
  return <>{children}</>;
}
