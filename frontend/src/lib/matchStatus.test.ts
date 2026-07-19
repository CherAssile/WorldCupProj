import { describe, expect, it } from "vitest";
import { deriveMatchStatus } from "./matchStatus";

const NOW = new Date("2026-07-17T12:00:00Z");

// Règle sensible (verrouillage) : cf. CLAUDE.md — un match se verrouille au coup
// d'envoi côté serveur ; ce test couvre la même règle côté client (affichage).
// Les équipes inconnues (placeholders) ne bloquent PLUS : le pronostic par côté
// (predicted_winner_side) rend ces matchs pronostiquables jusqu'au coup d'envoi.
describe("deriveMatchStatus", () => {
  it("est éditable avant le coup d'envoi", () => {
    expect(deriveMatchStatus({ kickoff_at: "2026-07-17T13:00:00Z" }, NOW)).toBe("editable");
  });

  it("est verrouillé après le coup d'envoi", () => {
    expect(deriveMatchStatus({ kickoff_at: "2026-07-17T11:00:00Z" }, NOW)).toBe("locked");
  });

  it("est verrouillé exactement au coup d'envoi (limite inclusive)", () => {
    expect(deriveMatchStatus({ kickoff_at: NOW.toISOString() }, NOW)).toBe("locked");
  });

  it("reste éditable avant le coup d'envoi même à équipes inconnues (placeholders)", () => {
    // Le statut ne dépend plus des équipes : un match à placeholders futur est éditable.
    expect(deriveMatchStatus({ kickoff_at: "2026-07-18T00:00:00Z" }, NOW)).toBe("editable");
  });

  it("reste verrouillé après le coup d'envoi même à équipes inconnues", () => {
    expect(deriveMatchStatus({ kickoff_at: "2026-07-01T00:00:00Z" }, NOW)).toBe("locked");
  });
});
