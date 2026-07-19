import type { MatchRead } from "../types/api";

/**
 * Ordonne les matchs d'une phase pour l'affichage en arbre. `num` (numéro de match
 * source) est le seul signal de position disponible côté API ; à défaut on retombe
 * sur l'ordre chronologique.
 */
export function sortBracketMatches(matches: MatchRead[]): MatchRead[] {
  return [...matches].sort((a, b) => {
    if (a.num !== null && b.num !== null) return a.num - b.num;
    if (a.num !== null) return -1;
    if (b.num !== null) return 1;
    return new Date(a.kickoff_at).getTime() - new Date(b.kickoff_at).getTime();
  });
}
