import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TeamPlayersGroup } from "../types/api";

// Doit rester synchronisé avec MIN_QUERY_LENGTH dans PlayerSearchSheet.tsx (ui/) :
// pas d'import croisé pour garder ce composant purement présentationnel.
const MIN_QUERY_LENGTH = 2;

export function usePlayerSearch(query: string) {
  const trimmed = query.trim();

  return useQuery({
    queryKey: ["players", "search", trimmed],
    queryFn: () => api.get<TeamPlayersGroup[]>(`/players?search=${encodeURIComponent(trimmed)}`),
    enabled: trimmed.length >= MIN_QUERY_LENGTH,
  });
}
