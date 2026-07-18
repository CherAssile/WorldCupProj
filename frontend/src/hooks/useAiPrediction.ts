import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { AiPredictionRead } from "../types/api";

/**
 * Prono IA d'un match. Les pronos IA sont pré-générés côté admin : un 404 signifie
 * simplement "pas encore disponible pour ce match", pas une vraie erreur à afficher.
 */
export function useAiPrediction(matchId: number | null) {
  return useQuery({
    queryKey: ["ai-prediction", matchId],
    queryFn: () => api.get<AiPredictionRead>(`/matches/${matchId}/ai-prediction`),
    enabled: matchId !== null,
    retry: false,
  });
}
