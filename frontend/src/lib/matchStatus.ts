import type { MatchRead } from "../types/api";

export type PredictionCardStatus = "editable" | "locked";

/**
 * Dérive l'état d'affichage d'un match à pronostiquer. Seul le coup d'envoi verrouille :
 * un match aux équipes encore inconnues (placeholders) reste pronostiquable — le qualifié
 * s'y exprime par le côté (predicted_winner_side). Cette vérification client est
 * indicative seulement — le serveur reste seul juge à l'enregistrement (409 si dépassé).
 */
export function deriveMatchStatus(
  match: Pick<MatchRead, "kickoff_at">,
  now: Date = new Date()
): PredictionCardStatus {
  return new Date(match.kickoff_at).getTime() <= now.getTime() ? "locked" : "editable";
}
