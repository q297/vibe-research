import { type FormEvent, useState } from "react";
import { ErrorBox } from "../components/ErrorBox";
import { useSession } from "../session";

export function LoginPage() {
  const { login } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-white">А</span>
          Альфа-Бизнес · прототип
        </div>
        <p className="text-sm text-slate-500">Демо-учётки описаны в README</p>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Логин"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Пароль"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error != null && <ErrorBox error={error} />}
        <button
          disabled={busy || !username || !password}
          className="w-full rounded-lg bg-brand py-2 font-medium text-white hover:bg-brand-dark disabled:opacity-50"
        >
          Войти
        </button>
      </form>
    </div>
  );
}
