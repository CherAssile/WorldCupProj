import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TrainingSessionCreate, TrainingSessionRead } from "../types/api";

/** Démarre une session d'entraînement : tirage aléatoire de matchs historiques côté serveur. */
export function useCreateTrainingSession() {
  return useMutation({
    mutationFn: (body: TrainingSessionCreate) => api.post<TrainingSessionRead>("/training/sessions", body),
  });
}
