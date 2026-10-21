import { ApiFailure } from "../api/client";

export function ErrorBox({ error }: { error: unknown }) {
  const failure = error instanceof ApiFailure ? error : null;
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      {failure?.error.code === "rate_limited"
        ? "Слишком много запросов, попробуйте позже"
        : (failure?.message ?? "Что-то пошло не так")}
      {failure?.error.trace_id && (
        <span className="ml-2 text-xs text-red-500">trace: {failure.error.trace_id}</span>
      )}
    </div>
  );
}
