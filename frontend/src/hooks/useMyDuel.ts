import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { DuelSummaryRead } from "../types/api";

/**
 * Duel cumulé de l'utilisateur contre l'IA en mode compétitif (lecture agrégée de
 * predictions + ai_predictions, cf. GET /me/duel-ia). Sert à la fois le bandeau d'accueil,
 * l'écran de détail, et l'enrichissement d'une carte de match terminé sur Pronostics.
 */
export function useMyDuel() {
  return useQuery({
    queryKey: ["me", "duel-ia"],
    queryFn: () => api.get<DuelSummaryRead>("/me/duel-ia"),
  });
}
