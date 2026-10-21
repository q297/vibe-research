import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";
import { useSession } from "../session";

// Polling instead of push, ingestion has no notifications (E6)
export function useFeed(limit = 20) {
  const { clientId, role } = useSession();
  return useQuery({
    queryKey: ["feed", clientId, role, limit],
    queryFn: () =>
      unwrap(
        api.GET("/v1/clients/{client_id}/feed", {
          params: { path: { client_id: clientId! }, query: { limit, role: role ?? undefined } },
        }),
      ),
    enabled: clientId !== null,
    refetchInterval: 60_000,
  });
}
