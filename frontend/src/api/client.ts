import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type ApiError = Schemas["ApiError"];

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const TOKEN_KEY = "alfa-news-token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Storage may be blocked, the session then lives until reload
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // Nothing to clear
    }
  },
};

export const LOGOUT_EVENT = "auth:logout";

const auth: Middleware = {
  onRequest({ request }) {
    const token = tokenStore.get();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401 && !response.url.endsWith("/auth/login")) {
      tokenStore.clear();
      window.dispatchEvent(new Event(LOGOUT_EVENT));
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: API_BASE });
api.use(auth);

export class ApiFailure extends Error {
  constructor(
    public readonly error: ApiError,
    public readonly status: number,
  ) {
    super(error.message);
  }
}

// Turns openapi-fetch results into plain values or a thrown ApiFailure for react-query
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call;
  if (error !== undefined || data === undefined) {
    const body = (error ?? {}) as Partial<ApiError>;
    throw new ApiFailure(
      {
        code: body.code ?? "internal",
        message: body.message ?? response.statusText,
        trace_id: body.trace_id ?? response.headers.get("X-Trace-Id"),
      },
      response.status,
    );
  }
  return data;
}
