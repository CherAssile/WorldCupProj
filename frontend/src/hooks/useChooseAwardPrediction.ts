import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../lib/api";
import type { AwardPredictionCreate, AwardPredictionRead } from "../types/api";

/**
 * Choisit un joueur pour une catégorie de récompense. Le serveur remplace le choix
 * précédent au lieu de le dupliquer (unicité gérée côté serveur, un seul POST suffit
 * toujours). Verrouillé à lock_at côté serveur : un 409 rafraîchit les catégories.
 */
export function useChooseAwardPrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AwardPredictionCreate) => api.post<AwardPredictionRead>("/award-predictions", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["award-predictions", "me"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        queryClient.invalidateQueries({ queryKey: ["awards"] });
      }
    },
  });
}
