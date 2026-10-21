import { Link } from "react-router-dom";
import { ErrorBox } from "../components/ErrorBox";
import { useSession } from "../session";
import { useFeed } from "./useFeed";

const ACCOUNTS = [
  { name: "Расчётный счёт", amount: "128 450 210,00 ₽" },
  { name: "Валютный счёт", amount: "1 204 300,00 ¥" },
  { name: "Депозит", amount: "300 000 000,00 ₽" },
];

export function HomePage() {
  const { clientId } = useSession();
  const feed = useFeed(3);

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="space-y-4 lg:col-span-2">
        {/* Permanent entry point on the main page (criterion 9) */}
        <div className="rounded-2xl bg-gradient-to-br from-brand to-brand-dark p-5 text-white shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Новости для вашего бизнеса</h2>
            <Link to="/news" className="rounded-lg bg-white/15 px-3 py-1.5 text-sm hover:bg-white/25">
              Все новости →
            </Link>
          </div>
          <p className="mt-1 text-sm text-white/80">
            Что происходит и как это влияет именно на вашу компанию
          </p>
          <div className="mt-4 space-y-2">
            {feed.isPending && <p className="text-sm text-white/70">Подбираем события…</p>}
            {feed.error && <ErrorBox error={feed.error} />}
            {feed.data?.items.map((item) => (
              <Link
                key={item.event.event_id}
                to={`/news/${clientId}/${item.event.event_id}`}
                className="block rounded-xl bg-white p-3 text-slate-900 hover:shadow"
              >
                <div className="font-medium">{item.event.title}</div>
                <div className="mt-1 text-xs text-slate-500">
                  Почему вам: {item.why_relevant?.map((r) => r.label).join(" · ")}
                </div>
              </Link>
            ))}
            {feed.data?.items.length === 0 && (
              <p className="text-sm text-white/80">Значимых событий для вашей компании пока нет</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="font-medium text-slate-500">Последние платежи</h3>
          <p className="mt-2 text-sm text-slate-400">Раздел интернет-банка (макет)</p>
        </div>
      </section>

      <aside className="space-y-3">
        {ACCOUNTS.map((a) => (
          <div key={a.name} className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-sm text-slate-500">{a.name}</div>
            <div className="mt-1 text-lg font-semibold">{a.amount}</div>
            <div className="text-xs text-slate-400">макет</div>
          </div>
        ))}
      </aside>
    </div>
  );
}
