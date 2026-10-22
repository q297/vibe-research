import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";
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
      <p className="text-xs text-slate-400">
        Пока работают заглушки агента, токены и стоимость равны нулю. Реальные значения придут из
        журнала вызовов LLM роли 4
      </p>
    </div>
  );
}
