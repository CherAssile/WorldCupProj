import { aiPointsBreakdownLabel, pointsBreakdownLabel } from "./pointsBreakdown";
import { frenchTeamName } from "./teamNamesFr";
import type { MatchDuelRead } from "../types/api";

export interface DuelCardSide {
  scoreLabel: string;
  breakdownLabel: string;
  points: number;
}

export interface DuelCardAiSide extends DuelCardSide {
  isFallback: boolean;
}

/** Équipe que l'utilisateur a désignée comme qualifiée (par id ou par côté, résolu une
 * fois les équipes connues) — pour l'afficher à côté du score, en clair. */
function qualifierPickLabel(entry: MatchDuelRead): string | null {
  if (entry.phase === "group") return null;
  let teamId = entry.user_predicted_winner_team_id;
  if (teamId === null && entry.user_predicted_winner_side !== null) {
    teamId = entry.user_predicted_winner_side === "home" ? (entry.home_team?.id ?? null) : (entry.away_team?.id ?? null);
  }
  if (teamId === null) return null;
  const team = entry.home_team?.id === teamId ? entry.home_team : entry.away_team?.id === teamId ? entry.away_team : null;
  return team ? `Qualifié coché : ${frenchTeamName(team.name)}` : null;
}

/**
 * Traduit une manche du duel (MatchDuelRead) en props prêtes pour FinishedMatchDuelCard :
 * libellés de score et détail des points, formatés une seule fois — réutilisé par la
 * carte de pronostic (écran Pronostics) et l'écran de détail du duel.
 */
export function buildDuelCardSides(entry: MatchDuelRead): { user: DuelCardSide | null; ai: DuelCardAiSide | null } {
  const isKnockout = entry.phase !== "group";

  const user: DuelCardSide | null =
    entry.user_points != null
      ? {
          scoreLabel: `${entry.user_predicted_home_score}–${entry.user_predicted_away_score}`,
          breakdownLabel: [
            pointsBreakdownLabel({
              scorePoints: entry.user_score_points ?? 0,
              qualifierPoints: entry.user_qualifier_points,
              doubled: entry.doubled,
              phase: entry.phase,
              total: entry.user_points,
              isKnockout,
            }),
            qualifierPickLabel(entry),
          ]
            .filter(Boolean)
            .join(" · "),
          points: entry.user_points,
        }
      : null;

  const ai: DuelCardAiSide | null =
    entry.ai_points != null
      ? {
          scoreLabel: `${entry.ai_predicted_home_score}–${entry.ai_predicted_away_score}`,
          breakdownLabel: aiPointsBreakdownLabel({
            // L'IA n'a pas de volet qualifié : ai_points = score_points x (2 si doublé),
            // toujours divisible exactement (0, 1 ou 3 points de base).
            scorePoints: entry.doubled ? entry.ai_points / 2 : entry.ai_points,
            doubled: entry.doubled,
            phase: entry.phase,
            total: entry.ai_points,
          }),
          points: entry.ai_points,
          isFallback: entry.ai_is_fallback ?? false,
        }
      : null;

  return { user, ai };
}
