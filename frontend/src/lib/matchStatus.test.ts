import { describe, expect, it } from "vitest";
import { deriveMatchStatus } from "./matchStatus";
import type { MatchRead } from "../types/api";

const TEAM_A = { id: 1, name: "France", fifa_code: "FRA", flag_url: null, group_name: null, coach_name: null, coach_photo_url: null };
const TEAM_B = { id: 2, name: "Argentine", fifa_code: "ARG", flag_url: null, group_name: null, coach_name: null, coach_photo_url: null };

const NOW = new Date("2026-07-17T12:00:00Z");

function match(overrides: Partial<Pick<MatchRead, "home_team" | "away_team" | "kickoff_at">>) {
  return {
    home_team: TEAM_A,
    away_team: TEAM_B,
    kickoff_at: "2026-07-17T13:00:00Z",
    ...overrides,
  };
}

// Règle sensible (verrouillage) : cf. CLAUDE.md — un match se verrouille au coup
// d'envoi côté serveur ; ce test couvre la même règle côté client (affichage).
describe("deriveMatchStatus", () => {
  it("est éditable avant le coup d'envoi, équipes connues", () => {
    expect(deriveMatchStatus(match({ kickoff_at: "2026-07-17T13:00:00Z" }), NOW)).toBe("editable");
  });

  it("est verrouillé après le coup d'envoi", () => {
    expect(deriveMatchStatus(match({ kickoff_at: "2026-07-17T11:00:00Z" }), NOW)).toBe("locked");
  });

  it("est verrouillé exactement au coup d'envoi (limite inclusive)", () => {
    expect(deriveMatchStatus(match({ kickoff_at: NOW.toISOString() }), NOW)).toBe("locked");
  });

  it("est en attente si l'équipe à domicile n'est pas encore connue, même avant le coup d'envoi", () => {
    expect(deriveMatchStatus(match({ home_team: null, kickoff_at: "2026-07-18T00:00:00Z" }), NOW)).toBe("pending");
  });

  it("est en attente si l'équipe à l'extérieur n'est pas encore connue", () => {
    expect(deriveMatchStatus(match({ away_team: null, kickoff_at: "2026-07-18T00:00:00Z" }), NOW)).toBe("pending");
  });

  it("priorise l'attente sur le verrouillage quand les deux s'appliqueraient", () => {
    expect(deriveMatchStatus(match({ home_team: null, kickoff_at: "2026-07-01T00:00:00Z" }), NOW)).toBe("pending");
  });
});
