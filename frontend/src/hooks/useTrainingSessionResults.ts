import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TrainingSessionResultsRead } from "../types/api";

/** Duel cumulé de la session (toi vs IA) — résultats déjà révélés + total des points. */
export function useTrainingSessionResults(sessionId: number | null) {
  return useQuery({
    queryKey: ["training-session-results", sessionId],
    queryFn: () => api.get<TrainingSessionResultsRead>(`/training/sessions/${sessionId}/results`),
    enabled: sessionId !== null,
  });
}
