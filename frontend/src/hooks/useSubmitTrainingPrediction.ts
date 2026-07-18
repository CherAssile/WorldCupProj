import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TrainingMatchResultRead, TrainingPredictionCreate } from "../types/api";

interface SubmitTrainingPredictionInput {
  sessionId: number;
  matchId: number;
  body: TrainingPredictionCreate;
}

/**
 * Soumet un pronostic d'entraînement pour un match. Le serveur révèle alors le vrai
 * score, les points obtenus et le prono de l'IA (TrainingMatchResultRead) — écrit
 * uniquement dans training_predictions, jamais dans predictions/scores/classement.
 */
export function useSubmitTrainingPrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, matchId, body }: SubmitTrainingPredictionInput) =>
      api.post<TrainingMatchResultRead>(`/training/sessions/${sessionId}/predictions/${matchId}`, body),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["training-session-results", variables.sessionId] });
    },
  });
}
