import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { api, LOGOUT_EVENT, type Schemas, tokenStore, unwrap } from "./api/client";

type Session = {
  me: Schemas["Me"] | null;
  loading: boolean;
  clientId: string | null;
  setClientId: (id: string) => void;
  role: Schemas["UserRole"] | null;
  setRole: (role: Schemas["UserRole"]) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const SessionContext = createContext<Session | null>(null);

// Selected client and role survive reloads, the user's access is still checked by the API
function readPref(key: string): string | null {
  try {
    return localStorage.getItem(`alfa-news-${key}`);
  } catch {
    return null;
  }
}

function writePref(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(`alfa-news-${key}`);
    else localStorage.setItem(`alfa-news-${key}`, value);
  } catch {
    // Preference is kept in memory only
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => tokenStore.get() !== null);
  const [clientId, setClientIdState] = useState<string | null>(() => readPref("clientId"));
  const [role, setRoleState] = useState<Schemas["UserRole"] | null>(
    () => readPref("role") as Schemas["UserRole"] | null,
  );
  const setClientId = (id: string | null) => {
    setClientIdState(id);
    writePref("clientId", id);
  };
  const setRole = (value: Schemas["UserRole"] | null) => {
    setRoleState(value);
    writePref("role", value);
  };

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => unwrap(api.GET("/v1/me")),
    enabled: hasToken,
    retry: false,
  });
  const me = hasToken ? (meQuery.data ?? null) : null;

  useEffect(() => {
    if (me && (!clientId || !me.client_ids.includes(clientId))) setClientId(me.client_ids[0] ?? null);
    if (me && !role) setRole(me.role);
  }, [me, clientId, role]);

  useEffect(() => {
    const onLogout = () => {
      setHasToken(false);
      queryClient.clear();
    };
    window.addEventListener(LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout);
  }, [queryClient]);

  const value: Session = {
    me,
    loading: hasToken && meQuery.isPending,
    clientId,
    setClientId,
    role,
    setRole,
    async login(username, password) {
      const token = await unwrap(api.POST("/v1/auth/login", { body: { username, password } }));
      tokenStore.set(token.access_token);
      setClientId(null);
      setRole(null);
      setHasToken(true);
    },
    logout() {
      tokenStore.clear();
      setHasToken(false);
      queryClient.clear();
    },
  };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession outside SessionProvider");
  return session;
}
