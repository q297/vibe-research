import type { Schemas } from "../api/client";
import { STEP_LABELS } from "../api/labels";
import { CitationLink } from "./Provenance";

const statusClass: Record<Schemas["StepStatus"], string> = {
  ok: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

export function TracePanel({
  steps,
  running,
  featuresUsed,
}: {
  steps: Schemas["TraceStep"][];
  running: boolean;
  featuresUsed?: string[];
}) {
  return (
    <details open className="rounded-xl border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer font-medium">
        Как получен вывод {running && <span className="text-sm text-slate-400">· агент работает…</span>}
      </summary>
      {featuresUsed && featuresUsed.length > 0 && (
        <p className="mt-3 text-xs text-slate-500">Признаки клиента: {featuresUsed.join(", ")}</p>
      )}
      <ol className="mt-3 space-y-3">
        {steps.map((s) => (
          <li key={s.index} className="flex gap-3">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${statusClass[s.status ?? "ok"]}`} />
            <div className="min-w-0 text-sm">
              <div>
                <span className="mr-2 text-xs uppercase tracking-wide text-slate-400">
                  {STEP_LABELS[s.kind]}
                </span>
                <span className="font-medium">{s.title}</span>
                {s.tool && <code className="ml-2 text-xs text-slate-500">{s.tool}</code>}
              </div>
              {s.detail && <p className="text-slate-600">{s.detail}</p>}
              {(s.input_summary || s.output_summary) && (
                <p className="text-xs text-slate-500">
                  {s.input_summary && <>вход: {s.input_summary} </>}
                  {s.output_summary && <>→ {s.output_summary}</>}
                </p>
              )}
              {s.citations && s.citations.length > 0 && (
                <div className="flex flex-wrap gap-x-3 text-xs">
                  {s.citations.map((c) => (
                    <CitationLink key={c.source_id} citation={c} />
                  ))}
                </div>
              )}
              {s.model && (
                <p className="text-xs text-slate-400">
                  {s.model}
                  {s.tokens_in != null && ` · ${s.tokens_in}+${s.tokens_out ?? 0} токенов`}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}
