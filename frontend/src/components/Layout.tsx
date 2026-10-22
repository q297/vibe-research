import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, type Schemas, unwrap } from "../api/client";
import { ROLE_LABELS } from "../api/labels";
import { useSession } from "../session";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap px-3 py-2 rounded-lg text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`;

export function Layout() {
  const { me, clientId, setClientId, role, setRole, logout } = useSession();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const clients = useQuery({ queryKey: ["clients"], queryFn: () => unwrap(api.GET("/v1/clients")) });
  const health = useQuery({ queryKey: ["health"], queryFn: () => unwrap(api.GET("/v1/health")) });
  const budget = useQuery({
    queryKey: ["budget"],
    queryFn: () => unwrap(api.GET("/v1/budget")),
    refetchInterval: 60_000,
  });

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-white">А</span>
            Альфа-Бизнес
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-normal text-slate-500">
              прототип
            </span>
          </div>
          <nav className="order-last -mx-1 flex w-full gap-1 overflow-x-auto px-1 md:order-none md:w-auto">
            <NavLink to="/" end className={navClass}>
              Главная
            </NavLink>
            <NavLink to="/news" end className={navClass}>
              Новости для бизнеса
            </NavLink>
            <NavLink to="/news/new" className={navClass}>
              Своя новость
            </NavLink>
            {me?.is_demo_admin && (
              <NavLink to="/metrics" className={navClass}>
                Качество
              </NavLink>
            )}
          </nav>
          <div className="ml-auto flex flex-wrap items-center gap-2 text-sm">
            {health.data?.mock_mode && (
              <span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">
                Синтетические данные
              </span>
            )}
            {clients.data && clients.data.length > 1 && (
              <select
                aria-label="Клиент"
                className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
                value={clientId ?? ""}
                onChange={(e) => {
                  setClientId(e.target.value);
                  if (/^\/news\/(?!new$)/.test(pathname)) navigate("/news");
                }}
              >
                {clients.data.map((c) => (
                  <option key={c.client_id} value={c.client_id}>
                    {c.display_name}
                  </option>
                ))}
              </select>
            )}
            <select
              aria-label="Роль"
              className="rounded-lg border border-slate-300 bg-white px-2 py-1.5"
              value={role ?? ""}
              onChange={(e) => setRole(e.target.value as Schemas["UserRole"])}
            >
              {Object.entries(ROLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <span className="hidden text-slate-500 md:inline">{me?.display_name}</span>
            <button className="text-slate-500 hover:text-slate-900" onClick={logout}>
              Выйти
            </button>
          </div>
        </div>
      </header>
      {/* Degraded modes: users still get cached insights, but no new ones */}
      {budget.data?.exhausted && (
        <div className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">
          Дневной лимит AI исчерпан. Готовые инсайты доступны, новые появятся завтра
        </div>
      )}
      {health.data?.offline_mode && (
        <div className="bg-slate-200 px-4 py-2 text-center text-sm text-slate-700">
          Офлайн-режим: показываем сохранённые новости и инсайты
        </div>
      )}
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
