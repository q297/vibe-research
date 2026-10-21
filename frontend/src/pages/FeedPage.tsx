import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";
import { ErrorBox } from "../components/ErrorBox";
import { FeedCard } from "../components/FeedCard";
import { ProvenanceLegend } from "../components/Provenance";
import { useSession } from "../session";
import { useFeed } from "./useFeed";

export function FeedPage() {
  const { clientId } = useSession();
  const feed = useFeed();
  const profile = useQuery({
    queryKey: ["profile", clientId],
    queryFn: () =>
      unwrap(
        api.GET("/v1/clients/{client_id}/profile", { params: { path: { client_id: clientId! } } }),
      ),
    enabled: clientId !== null,
  });

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="space-y-3 lg:col-span-2">
        <h1 className="text-xl font-semibold">Новости для вашего бизнеса</h1>
        {feed.isPending && <p className="text-slate-500">Загрузка…</p>}
        {feed.error && <ErrorBox error={feed.error} />}
        {feed.data?.items.map((item) => (
          <FeedCard key={item.event.event_id} item={item} clientId={clientId!} />
        ))}
      </section>

      <aside className="space-y-4">
        {profile.data && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm">
            <h2 className="font-medium">{profile.data.display_name}</h2>
            <p className="mt-1 text-slate-500">
              {profile.data.okved_code} · {profile.data.okved_name}
            </p>
            <p className="text-slate-500">{profile.data.region ?? "Регион не определён"}</p>
            <h3 className="mt-3 text-xs uppercase tracking-wide text-slate-400">
              Чувствительность
            </h3>
            <ul className="mt-1 space-y-1">
              {profile.data.sensitivities?.map((s) => (
                <li key={s.tag} className="flex items-center gap-2">
                  <span className="h-1.5 rounded bg-brand" style={{ width: `${s.weight * 48}px` }} />
                  <span>{s.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm">
          <h3 className="mb-2 text-xs uppercase tracking-wide text-slate-400">Обозначения</h3>
          <ProvenanceLegend />
        </div>
      </aside>
    </div>
  );
}
