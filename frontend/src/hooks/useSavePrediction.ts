import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../lib/api";
import type { PredictionCreate, PredictionRead, PredictionUpdate } from "../types/api";

interface SavePredictionInput {
  existingId: number | null;
  matchId: number;
  predictedHomeScore: number;
  predictedAwayScore: number;
  /** Mutuellement exclusifs (règle serveur) : par équipe si connues, par côté sinon. */
  predictedWinnerTeamId: number | null;
  predictedWinnerSide: "home" | "away" | null;
}

/**
 * Crée (POST) ou met à jour (PUT) un pronostic selon qu'il existe déjà.
 * Le serveur fait foi sur le verrouillage : un 409 (kickoff dépassé) invalide
 * la liste des matchs pour que l'écran se remette à jour tout seul.
 */
export function useSavePrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: SavePredictionInput) => {
      if (input.existingId) {
        const body: PredictionUpdate = {
          predicted_home_score: input.predictedHomeScore,
          predicted_away_score: input.predictedAwayScore,
          predicted_winner_team_id: input.predictedWinnerTeamId,
          predicted_winner_side: input.predictedWinnerSide,
        };
        return api.put<PredictionRead>(`/predictions/${input.existingId}`, body);
      }

      const body: PredictionCreate = {
        match_id: input.matchId,
        predicted_home_score: input.predictedHomeScore,
        predicted_away_score: input.predictedAwayScore,
        predicted_winner_team_id: input.predictedWinnerTeamId,
        predicted_winner_side: input.predictedWinnerSide,
      };
      return api.post<PredictionRead>("/predictions", body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["predictions", "me"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        queryClient.invalidateQueries({ queryKey: ["matches"] });
      }
    },
  });
}
