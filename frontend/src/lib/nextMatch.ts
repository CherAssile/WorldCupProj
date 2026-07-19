import { deriveMatchStatus } from "./matchStatus";
import type { MatchPhaseGroup, MatchRead } from "../types/api";

/**
 * Premier match à venir et non verrouillé, toutes phases confondues (groupes inclus).
 * Les matchs aux équipes encore inconnues (placeholders) comptent aussi : ils sont
 * pronostiquables jusqu'au coup d'envoi (qualifié par côté).
 */
export function findNextMatch(groups: MatchPhaseGroup[]): MatchRead | null {
  const upcoming = groups
    .flatMap((group) => group.matches)
    .filter((match) => deriveMatchStatus(match) === "editable")
    .sort((a, b) => new Date(a.kickoff_at).getTime() - new Date(b.kickoff_at).getTime());

  return upcoming[0] ?? null;
}
