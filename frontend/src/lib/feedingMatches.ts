import type { MatchRead } from "../types/api";

/** Numéro de match référencé par un placeholder (« W101 » → 101), ou null si absent. */
export function referencedMatchNum(placeholder: string | null): number | null {
  if (!placeholder) return null;
  const digits = placeholder.match(/\d+/);
  return digits ? Number(digits[0]) : null;
}

/** Index des matchs par leur numéro source (num), pour retrouver un match référencé. */
export function indexByNum(matches: MatchRead[]): Map<number, MatchRead> {
  const byNum = new Map<number, MatchRead>();
  for (const match of matches) {
    if (match.num !== null) byNum.set(match.num, match);
  }
  return byNum;
}

/**
 * Les deux matchs qui alimentent un match à placeholders (ex. les deux demi-finales
 * d'une finale, ou celles dont les perdants jouent la petite finale). null quand le
 * match référencé n'est pas retrouvé ou que le côté n'est pas un placeholder.
 */
export function feedingMatches(
  match: MatchRead,
  byNum: Map<number, MatchRead>
): { home: MatchRead | null; away: MatchRead | null } {
  const homeNum = referencedMatchNum(match.home_placeholder);
  const awayNum = referencedMatchNum(match.away_placeholder);
  return {
    home: homeNum !== null ? byNum.get(homeNum) ?? null : null,
    away: awayNum !== null ? byNum.get(awayNum) ?? null : null,
  };
}
