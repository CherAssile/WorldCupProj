import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TrainingSessionRead } from "../types/api";

/**
 * Charge une session d'entraînement : liste des matchs tirés, sans jamais exposer leur
 * score réel (anti-triche côté serveur — le champ n'existe pas dans TrainingMatchRead).
 */
export function useTrainingSession(sessionId: number | null) {
  return useQuery({
    queryKey: ["training-session", sessionId],
    queryFn: () => api.get<TrainingSessionRead>(`/training/sessions/${sessionId}`),
    enabled: sessionId !== null,
  });
}
