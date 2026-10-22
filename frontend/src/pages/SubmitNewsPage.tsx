import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, unwrap } from "../api/client";
import { ErrorBox } from "../components/ErrorBox";
import { useSession } from "../session";

const MIN_LENGTH = 40;
const MAX_LENGTH = 10_000;

// Live demo of criterion 5: any new text goes through classification and the agent
export function SubmitNewsPage() {
  const { clientId } = useSession();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");

  const submit = useMutation({
    // No client_id here: the insight page starts the agent with the selected role
    mutationFn: () =>
      unwrap(
        api.POST("/v1/news/ingest", {
          body: { text: text.trim(), title: title.trim() || null, url: url.trim() || null },
        }),
      ),
    onSuccess: (data) => navigate(`/news/${clientId}/${data.event.event_id}`),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit.mutate();
  }

  const length = text.trim().length;
  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Проверить свою новость</h1>
        <p className="mt-1 text-sm text-slate-500">
          Вставьте текст новости: система определит тему и покажет, что она значит для выбранной
          компании. Текст не проверяется, поэтому выводы по нему помечаются как основанные на
          введённых данных
        </p>
      </div>
      <input
        className="w-full rounded-lg border border-slate-300 px-3 py-2"
        placeholder="Заголовок (необязательно)"
        maxLength={300}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        className="h-56 w-full rounded-lg border border-slate-300 px-3 py-2"
        placeholder="Текст новости"
        maxLength={MAX_LENGTH}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="flex justify-between text-xs text-slate-400">
        <span>{length < MIN_LENGTH ? `Минимум ${MIN_LENGTH} символов` : ""}</span>
        <span>
          {length} / {MAX_LENGTH}
        </span>
      </div>
      <input
        className="w-full rounded-lg border border-slate-300 px-3 py-2"
        placeholder="Ссылка на источник (необязательно)"
        type="url"
        maxLength={2000}
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      {submit.error && <ErrorBox error={submit.error} />}
      <button
        disabled={submit.isPending || length < MIN_LENGTH || !clientId}
        className="rounded-lg bg-brand px-5 py-2 font-medium text-white hover:bg-brand-dark disabled:opacity-50"
      >
        {submit.isPending ? "Классифицируем…" : "Проанализировать"}
      </button>
    </form>
  );
}
