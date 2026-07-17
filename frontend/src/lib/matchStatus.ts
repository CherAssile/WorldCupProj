import type { MatchRead } from "../types/api";

export type PredictionCardStatus = "editable" | "locked" | "pending";

/**
 * Dérive l'état d'affichage d'un match à pronostiquer.
 * "pending" prime toujours sur le verrouillage : un match aux équipes encore
 * inconnues (placeholders) ne peut de toute façon pas être pronostiqué.
 * Le verrouillage lui-même est une vérification client, indicative seulement —
 * le serveur reste seul juge au moment de l'enregistrement (409 si dépassé).
 */
export function deriveMatchStatus(
  match: Pick<MatchRead, "home_team" | "away_team" | "kickoff_at">,
  now: Date = new Date()
): PredictionCardStatus {
  if (!match.home_team || !match.away_team) {
    return "pending";
  }
  return new Date(match.kickoff_at).getTime() <= now.getTime() ? "locked" : "editable";
}
