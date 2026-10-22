import { useState } from "react";
import { Link } from "react-router-dom";
import type { Schemas } from "../api/client";

const VISIBLE_REASONS = 3;

const dateFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" });

export function FeedCard({ item, clientId }: { item: Schemas["FeedItem"]; clientId: string }) {
  const { event } = item;
  const [expanded, setExpanded] = useState(false);
  const reasons = item.why_relevant ?? [];
  const hidden = reasons.length - VISIBLE_REASONS;
  const visible = expanded ? reasons : reasons.slice(0, VISIBLE_REASONS);
  const date = event.published_at ? dateFormat.format(new Date(event.published_at)) : null;
  return (
    <Link
      to={`/news/${clientId}/${event.event_id}`}
      className="block rounded-xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-medium">{event.title}</h3>
        {item.insight_status === "ready" && (
          <span className="shrink-0 rounded bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
            Инсайт готов
          </span>
        )}
        {item.insight_status === "stale" && (
          <span className="shrink-0 rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
            Есть обновления
          </span>
        )}
      </div>
      {event.summary && <p className="mt-1 text-sm text-slate-600">{event.summary}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-slate-400">Почему вам:</span>
        {visible.map((r) => (
          <span
            key={`${r.feature}:${r.label}`}
            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
          >
            {r.label}
          </span>
        ))}
        {hidden > 0 && (
          <button
            type="button"
            className="text-xs text-slate-500 underline-offset-2 hover:underline"
            onClick={(e) => {
              // The whole card is a link, the toggle must not navigate
              e.preventDefault();
              setExpanded((v) => !v);
            }}
          >
            {expanded ? "свернуть" : `ещё ${hidden}`}
          </button>
        )}
      </div>
      <div className="mt-2 flex gap-3 text-xs text-slate-400">
        {date && <span>{date}</span>}
        <span>Источников: {event.source_count}</span>
        {event.origin === "synthetic" && <span>синтетическая</span>}
      </div>
    </Link>
  );
}
