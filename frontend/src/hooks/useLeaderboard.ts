import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { LeaderboardEntryRead } from "../types/api";

// Pas de push serveur : le classement ne change qu'après une synchro de résultats
// (ponctuelle), donc un intervalle d'une minute suffit largement sans matraquer l'API.
const REFETCH_INTERVAL_MS = 60_000;

export function useLeaderboard() {
  return useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => api.get<LeaderboardEntryRead[]>("/leaderboard"),
    refetchInterval: REFETCH_INTERVAL_MS,
  });
}
