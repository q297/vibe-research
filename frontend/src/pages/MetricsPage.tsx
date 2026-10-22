import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, type Schemas, unwrap } from "../api/client";
import { ROLE_LABELS } from "../api/labels";
import { ErrorBox } from "../components/ErrorBox";

const number = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 });

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

// Run before the demo, so judges see ready insights and the budget stays for live news
function WarmupPanel() {
  const queryClient = useQueryClient();
  const [top, setTop] = useState(5);
  const [allRoles, setAllRoles] = useState(false);
  const status = useQuery({
    queryKey: ["warmup"],
    queryFn: () => unwrap(api.GET("/v1/admin/warm-cache")),
    refetchInterval: (q) => (q.state.data?.running ? 1_000 : false),
  });
  const start = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/v1/admin/warm-cache", {
          body: {
            top,
            roles: allRoles ? (Object.keys(ROLE_LABELS) as Schemas["UserRole"][]) : null,
            force: false,
          },
        }),
      ),
    onSuccess: (data) => queryClient.setQueryData(["warmup"], data),
  });
  const s = status.data;
  const done = s ? s.computed + s.skipped + s.failed : 0;

  useEffect(() => {
    if (s && !s.running && s.finished_at) {
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      queryClient.invalidateQueries({ queryKey: ["feed"] });
    }
  }, [s, queryClient]);

  return (
    <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
      <div>
        <h2 className="font-medium">Подготовка к демо</h2>
        <p className="text-sm text-slate-500">
          Заранее строит инсайты для верхних новостей в ленте каждой компании. Уже готовые и
          актуальные пропускаются, поэтому повторный запуск почти не тратит бюджет
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          Новостей на компанию
          <input
            type="number"
            min={1}
            max={20}
            value={top}
            onChange={(e) => setTop(Math.min(20, Math.max(1, Number(e.target.value) || 1)))}
            className="w-16 rounded-lg border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={allRoles} onChange={(e) => setAllRoles(e.target.checked)} />
          Для всех ролей
        </label>
        <button
          onClick={() => start.mutate()}
          disabled={start.isPending || s?.running}
          className="rounded-lg bg-slate-900 px-4 py-1.5 text-white disabled:opacity-50"
        >
          {s?.running ? "Идёт подготовка…" : "Подготовить инсайты"}
        </button>
      </div>
      {s && s.total > 0 && (
        <div className="space-y-1 text-sm">
          <div className="h-2 overflow-hidden rounded bg-slate-100">
            <div className="h-full bg-emerald-500" style={{ width: `${(done / s.total) * 100}%` }} />
          </div>
          <p className="text-slate-600">
            {done} из {s.total} · построено {s.computed} · уже были готовы {s.skipped}
            {s.failed > 0 && ` · ошибок ${s.failed}`}
          </p>
          {s.current && <p className="text-xs text-slate-400">Сейчас: {s.current}</p>}
        </div>
      )}
      {s?.error && <ErrorBox error={new Error(s.error)} />}
      {start.error && <ErrorBox error={start.error} />}
    </section>
  );
}

const share = (part: number, total: number) =>
  total > 0 ? `${Math.round((part / total) * 100)}%` : "—";

// Quality and cost of the pipeline (criterion 8), visible to the demo admin
export function MetricsPage() {
  const metrics = useQuery({
    queryKey: ["metrics"],
    queryFn: () => unwrap(api.GET("/v1/metrics")),
    refetchInterval: 30_000,
  });
  const budget = useQuery({
    queryKey: ["budget"],
    queryFn: () => unwrap(api.GET("/v1/budget")),
    refetchInterval: 30_000,
  });

  if (metrics.error) return <ErrorBox error={metrics.error} />;
  const m = metrics.data;
  const b = budget.data;
  const rated = m ? m.feedback_up + m.feedback_down : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Качество и бюджет</h1>
      {m && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Tile label="Инсайтов построено" value={number.format(m.insights_total)} />
          <Tile
            label="Полезных по оценкам"
            value={share(m.feedback_up, rated)}
            hint={`👍 ${m.feedback_up} · 👎 ${m.feedback_down}`}
          />
          <Tile
            label="Самокоррекция агента"
            value={share(m.self_corrections, m.insights_total)}
            hint={`инсайтов с повтором после критика: ${m.self_corrections}`}
          />
          <Tile
            label="Время построения"
            value={m.avg_latency_ms != null ? `${number.format(m.avg_latency_ms / 1000)} с` : "—"}
            hint="в среднем на инсайт"
          />
        </section>
      )}
      {b && (
        <section className="grid gap-3 sm:grid-cols-3">
          <Tile
            label="Токенов сегодня"
            value={number.format(b.tokens_used_today)}
            hint={b.tokens_limit_today ? `лимит ${number.format(b.tokens_limit_today)}` : "лимит не задан"}
          />
          <Tile
            label="Стоимость сегодня"
            value={b.cost_rub_today != null ? `${number.format(b.cost_rub_today)} ₽` : "—"}
          />
          <Tile
            label="Токенов на инсайт"
            value={m?.avg_tokens_per_insight != null ? number.format(m.avg_tokens_per_insight) : "—"}
          />
        </section>
      )}
      <WarmupPanel />
      <p className="text-xs text-slate-400">
        Пока работают заглушки агента, токены и стоимость равны нулю. Реальные значения придут из
        журнала вызовов LLM роли 4
      </p>
    </div>
  );
}
