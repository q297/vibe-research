import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Schemas, unwrap } from "../api/client";
import { JOB_ERRORS, LEVEL_LABELS, TAG_LABELS } from "../api/labels";
import { streamJob } from "../api/stream";
import { ErrorBox } from "../components/ErrorBox";
import { CitationLink, ClaimView, ProvenanceBadge } from "../components/Provenance";
import { TracePanel } from "../components/TracePanel";
import { useSession } from "../session";

function useInsightJob(clientId: string, eventId: string, role: Schemas["UserRole"] | null) {
  const queryClient = useQueryClient();
  const [steps, setSteps] = useState<Schemas["TraceStep"][]>([]);
  const [job, setJob] = useState<Schemas["Job"] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!role) return;
    const controller = new AbortController();
    setSteps([]);
    setJob(null);
    setError(null);
    (async () => {
      const started = await unwrap(
        api.POST("/v1/clients/{client_id}/insights/{event_id}/run", {
          params: { path: { client_id: clientId, event_id: eventId } },
          body: { role, force: nonce > 0 },
        }),
      );
      setJob(started);
      if (started.status === "done" && started.insight_id) {
        const trace = await unwrap(
          api.GET("/v1/insights/{insight_id}/trace", {
            params: { path: { insight_id: started.insight_id } },
          }),
        );
        setSteps(trace.steps ?? []);
        return;
      }
      await streamJob(
        started.job_id,
        { onStep: (s) => setSteps((prev) => [...prev, s]), onJob: setJob },
        controller.signal,
      );
      queryClient.invalidateQueries({ queryKey: ["feed"] });
    })().catch((err) => {
      if (!controller.signal.aborted) setError(err);
    });
    return () => controller.abort();
  }, [clientId, eventId, role, nonce, queryClient]);

  return { steps, job, error, rerun: () => setNonce((n) => n + 1) };
}

export function InsightPage() {
  const { clientId = "", eventId = "" } = useParams();
  const { me, role, clientId: selectedClientId, setClientId } = useSession();
  const { steps, job, error, rerun } = useInsightJob(clientId, eventId, role);

  // A shared link may point to another client, keep the header switcher in sync
  useEffect(() => {
    if (clientId !== selectedClientId && me?.client_ids.includes(clientId)) setClientId(clientId);
  }, [clientId, selectedClientId, me, setClientId]);
  const insightId = job?.status === "done" ? job.insight_id : null;
  const event = useQuery({
    queryKey: ["event", eventId],
    queryFn: () =>
      unwrap(api.GET("/v1/events/{event_id}", { params: { path: { event_id: eventId } } })),
  });

  const insight = useQuery({
    queryKey: ["insight", insightId],
    queryFn: () =>
      unwrap(api.GET("/v1/insights/{insight_id}", { params: { path: { insight_id: insightId! } } })),
    enabled: !!insightId,
  });
  const running = !!job && job.status !== "done" && job.status !== "failed";

  return (
    <div className="space-y-4">
      <Link to="/news" className="text-sm text-slate-500 hover:text-slate-900">
        ← Все новости
      </Link>
      {event.data && <EventHeader event={event.data} />}
      {error != null && <ErrorBox error={error} />}
      {job?.status === "failed" && <JobError job={job} onRetry={rerun} />}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {!insight.data && (running || !job) && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">
              Агент анализирует событие для вашей компании…
            </div>
          )}
          {insight.data && <InsightCard insight={insight.data} onRerun={rerun} />}
          {insight.data && <Chat insightId={insight.data.insight_id} />}
        </div>
        <aside>
          <TracePanel
            steps={steps}
            running={running}
            featuresUsed={insight.data?.client_features_used}
          />
        </aside>
      </div>
    </div>
  );
}

function EventHeader({ event }: { event: Schemas["Event"] }) {
  const userInput = event.origin === "user_input";
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {userInput && (
        <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
          Введено пользователем · не проверено
        </span>
      )}
      {event.classification_status !== "classified" && (
        <span className="rounded bg-slate-200 px-2 py-0.5 text-slate-700">Тема не определена</span>
      )}
      {event.tags?.map((t) => (
        <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
          {TAG_LABELS[t]}
        </span>
      ))}
      {!userInput && <span className="text-slate-400">Источников: {event.articles?.length ?? 0}</span>}
    </div>
  );
}

function JobError({ job, onRetry }: { job: Schemas["Job"]; onRetry: () => void }) {
  const message = (job.error_code && JOB_ERRORS[job.error_code]) ?? "Не удалось построить инсайт";
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <span>{message}</span>
      {job.error && job.error_code !== "budget_exhausted" && (
        <span className="text-xs text-red-500">{job.error}</span>
      )}
      <span className="text-xs text-red-400">trace: {job.trace_id}</span>
      {job.error_code !== "budget_exhausted" && (
        <button onClick={onRetry} className="ml-auto underline">
          Повторить
        </button>
      )}
    </div>
  );
}

function CriticStatus({ insight }: { insight: Schemas["Insight"] }) {
  if (insight.critic_passed == null && !insight.confidence) return null;
  const passed = insight.critic_passed !== false;
  return (
    <div className={`rounded-lg p-3 text-sm ${passed ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
      <div className="flex flex-wrap gap-x-4">
        {insight.critic_passed != null && (
          <span>{passed ? "Проверено критиком" : "Критик нашёл проблемы, вывод может быть неполным"}</span>
        )}
        {insight.confidence && <span>Уверенность: {LEVEL_LABELS[insight.confidence]}</span>}
      </div>
      {insight.critic_notes && insight.critic_notes.length > 0 && (
        <ul className="mt-1 list-inside list-disc text-xs">
          {insight.critic_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs uppercase tracking-wide text-slate-400">{title}</h3>
      {children}
    </section>
  );
}

function InsightCard({ insight, onRerun }: { insight: Schemas["Insight"]; onRerun: () => void }) {
  return (
    <article className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-xl font-semibold">{insight.headline}</h1>
        <button onClick={onRerun} className="shrink-0 text-sm text-slate-500 hover:text-slate-900">
          Пересчитать
        </button>
      </div>
      {insight.status === "stale" && (
        <p className="rounded-lg bg-amber-50 p-2 text-sm text-amber-800">
          Событие обновилось после расчёта инсайта
        </p>
      )}

      <CriticStatus insight={insight} />

      <Section title="Что произошло">
        {insight.what_happened?.map((c, i) => <ClaimView key={i} claim={c} />)}
      </Section>
      <Section title="Почему это важно для вас">
        {insight.why_it_matters?.map((c, i) => <ClaimView key={i} claim={c} />)}
      </Section>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Риски">
          {insight.risks?.map((r, i) => (
            <div key={i} className="rounded-lg bg-red-50/60 p-3">
              <ClaimView claim={r.claim} />
              <p className="mt-1 text-xs text-slate-500">Уровень: {LEVEL_LABELS[r.severity ?? "medium"]}</p>
            </div>
          ))}
        </Section>
        <Section title="Возможности">
          {insight.opportunities?.map((o, i) => (
            <div key={i} className="rounded-lg bg-emerald-50/60 p-3">
              <ClaimView claim={o.claim} />
            </div>
          ))}
        </Section>
      </div>

      {insight.scenarios && insight.scenarios.length > 0 && (
        <Section title="На что обратить внимание дальше">
          {insight.scenarios.map((c, i) => (
            <ClaimView key={i} claim={c} />
          ))}
        </Section>
      )}

      {insight.actions?.some((a) => !a.is_promo) && (
        <Section title="Что делать">
          {insight.actions
            .filter((a) => !a.is_promo)
            .map((a, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <ProvenanceBadge provenance={a.provenance ?? "ai_inference"} />
                <span>{a.text}</span>
              </div>
            ))}
        </Section>
      )}

      {/* Bank offers are advertising, kept apart from AI conclusions */}
      {insight.actions?.some((a) => a.is_promo) && (
        <Section title="Предложения Альфа-Банка">
          {insight.actions
            .filter((a) => a.is_promo)
            .map((a, i) => (
              <div key={i} className="flex items-start gap-2 rounded-lg border border-brand/20 bg-brand/5 p-3 text-sm">
                <span className="shrink-0 rounded bg-brand px-2 py-0.5 text-xs text-white">Реклама</span>
                <span>{a.text}</span>
                {a.product_hint && (
                  <span className="ml-auto shrink-0 text-xs font-medium text-brand">{a.product_hint}</span>
                )}
              </div>
            ))}
        </Section>
      )}

      <Section title="Позиция Альфа-Банка">
        {insight.bank_positions?.map((p) => (
          <div key={p.position_id} className="rounded-lg border border-bank/20 bg-bank/5 p-3 text-sm">
            <div className="flex items-start gap-2">
              <ProvenanceBadge provenance="bank_position" />
              <span>{p.statement}</span>
            </div>
            <div className="mt-1 text-xs">
              <CitationLink citation={p.citation} />
            </div>
          </div>
        ))}
      </Section>

      {insight.data_gaps && insight.data_gaps.length > 0 && (
        <Section title="Чего не хватило агенту">
          <ul className="list-inside list-disc text-sm text-slate-600">
            {insight.data_gaps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </Section>
      )}

      <Feedback insightId={insight.insight_id} />
    </article>
  );
}

function Feedback({ insightId }: { insightId: string }) {
  const send = useMutation({
    mutationFn: (rating: Schemas["Rating"]) =>
      unwrap(api.POST("/v1/feedback", { body: { insight_id: insightId, rating } })),
  });
  if (send.isSuccess) return <p className="text-sm text-slate-500">Спасибо за оценку</p>;
  return (
    <div className="flex items-center gap-2 border-t border-slate-100 pt-4 text-sm">
      <span className="text-slate-500">Полезен ли инсайт?</span>
      <button className="rounded-lg border px-3 py-1 hover:bg-slate-50" onClick={() => send.mutate("up")}>
        👍
      </button>
      <button className="rounded-lg border px-3 py-1 hover:bg-slate-50" onClick={() => send.mutate("down")}>
        👎
      </button>
      {send.error && <ErrorBox error={send.error} />}
    </div>
  );
}

const SUGGESTIONS = ["А если ставка вырастет?", "Как это касается моих контрагентов?", "Покажи первоисточник"];

function Chat({ insightId }: { insightId: string }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const history = useQuery({
    queryKey: ["chat", insightId],
    queryFn: () =>
      unwrap(api.GET("/v1/insights/{insight_id}/chat", { params: { path: { insight_id: insightId } } })),
  });
  const send = useMutation({
    mutationFn: (message: string) =>
      unwrap(
        api.POST("/v1/insights/{insight_id}/chat", {
          params: { path: { insight_id: insightId } },
          body: { message },
        }),
      ),
    onSuccess: () => {
      setText("");
      queryClient.invalidateQueries({ queryKey: ["chat", insightId] });
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (text.trim()) send.mutate(text.trim());
  }

  return (
    <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6">
      <h2 className="font-medium">Вопрос по инсайту</h2>
      <div className="space-y-2">
        {history.data?.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg p-3 text-sm ${m.role === "user" ? "ml-8 bg-slate-100" : "mr-8 bg-ai/5"}`}
          >
            {m.provenance && <ProvenanceBadge provenance={m.provenance} />} {m.content}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => send.mutate(s)}
            className="rounded-full border px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            {s}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          placeholder="Спросите о последствиях для компании"
          value={text}
          maxLength={2000}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          disabled={send.isPending}
          className="rounded-lg bg-slate-900 px-4 text-sm text-white disabled:opacity-50"
        >
          Отправить
        </button>
      </form>
      {send.error && <ErrorBox error={send.error} />}
    </section>
  );
}
