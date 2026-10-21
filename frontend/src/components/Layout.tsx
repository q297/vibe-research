import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, type Schemas, unwrap } from "../api/client";
import { ROLE_LABELS } from "../api/labels";
import { useSession } from "../session";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-lg text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`;

export function Layout() {
  const { me, clientId, setClientId, role, setRole, logout } = useSession();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const clients = useQuery({ queryKey: ["clients"], queryFn: () => unwrap(api.GET("/v1/clients")) });
  const health = useQuery({ queryKey: ["health"], queryFn: () => unwrap(api.GET("/v1/health")) });

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
          <nav className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              Главная
            </NavLink>
            <NavLink to="/news" className={navClass}>
              Новости для бизнеса
            </NavLink>
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
                  if (pathname.startsWith("/news/")) navigate("/news");
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
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
