const PHASE_LABELS_LOWER: Record<string, string> = {
  quarter_final: "quart de finale",
  semi_final: "demi-finale",
  third_place: "petite finale",
  final: "finale",
};

/** Libellé bas de casse de la phase, pour "× 2 (demi-finale)" — replie sur le code brut
 * si la phase n'est pas censée être doublée (ne devrait pas être appelé dans ce cas). */
function phaseLabelLower(phase: string): string {
  return PHASE_LABELS_LOWER[phase] ?? phase;
}

/**
 * Détail des points d'un pronostic pour l'affichage : « 3 pts (score exact) + 2 pts (bon
 * qualifié) = 5 pts », doublé « (…) × 2 (demi-finale) = 10 pts ». Assemblage de texte pur
 * (le calcul des points reste une vérité backend, cf. services/scoring.py) : `isKnockout`
 * détermine si le volet qualifié doit apparaître (absent en poule).
 */
export function pointsBreakdownLabel(params: {
  scorePoints: number;
  qualifierPoints: number | null;
  doubled: boolean;
  phase: string;
  total: number;
  isKnockout: boolean;
}): string {
  const { scorePoints, qualifierPoints, doubled, phase, total, isKnockout } = params;
  const parts: string[] = [];
  if (scorePoints === 3) parts.push("3 pts (score exact)");
  else if (scorePoints === 1) parts.push("1 pt (issue correcte)");
  else parts.push("0 pt (score raté)");

  if (isKnockout) {
    parts.push(qualifierPoints === 2 ? "2 pts (bon qualifié)" : "0 pt (qualifié raté)");
  }

  const base = parts.join(" + ");
  if (doubled) {
    return `(${base}) × 2 (${phaseLabelLower(phase)}) = ${total} pt${total !== 1 ? "s" : ""}`;
  }
  return `${base} = ${total} pt${total !== 1 ? "s" : ""}`;
}

/** Même principe pour l'IA, jamais de volet qualifié (elle n'en pronostique pas). */
export function aiPointsBreakdownLabel(params: {
  scorePoints: number;
  doubled: boolean;
  phase: string;
  total: number;
}): string {
  const { scorePoints, doubled, phase, total } = params;
  const base = scorePoints === 3 ? "3 pts (score exact)" : scorePoints === 1 ? "1 pt (issue correcte)" : "0 pt (score raté)";
  if (doubled) {
    return `${base} × 2 (${phaseLabelLower(phase)}) = ${total} pt${total !== 1 ? "s" : ""}`;
  }
  return `${base} = ${total} pt${total !== 1 ? "s" : ""}`;
}
