import type { MatchRead } from "../types/api";

const PLACEHOLDER_PATTERN = /^([WL])(\d+)$/;

/**
 * Résout un placeholder brut ("W101" / "L101") en libellé lisible.
 * Format confirmé côté service IA (openfootball) : W<num> = vainqueur du match <num>,
 * L<num> = perdant du match <num>. Retombe sur le texte brut si le format est inattendu.
 */
export function resolvePlaceholderLabel(placeholder: string | null): string | null {
  if (!placeholder) return null;
  const match = placeholder.match(PLACEHOLDER_PATTERN);
  if (!match) return placeholder;
  const [, kind, num] = match;
  return kind === "W" ? `Vainqueur du match ${num}` : `Perdant du match ${num}`;
}

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
