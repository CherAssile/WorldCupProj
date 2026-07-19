import { describe, expect, it } from "vitest";
import { feedingMatches, indexByNum, referencedMatchNum } from "./feedingMatches";
import type { MatchRead } from "../types/api";

function match(overrides: Partial<MatchRead>): MatchRead {
  return {
    id: 0,
    num: null,
    phase: "final",
    status: "scheduled",
    kickoff_at: "2026-07-19T19:00:00Z",
    home_team: null,
    away_team: null,
    home_placeholder: null,
    away_placeholder: null,
    home_placeholder_label: null,
    away_placeholder_label: null,
    home_placeholder_label_short: null,
    away_placeholder_label_short: null,
    home_score: null,
    away_score: null,
    extra_time_home_score: null,
    extra_time_away_score: null,
    penalties_home_score: null,
    penalties_away_score: null,
    winner_team: null,
    ...overrides,
  };
}

describe("referencedMatchNum", () => {
  it("extrait le numéro d'un placeholder", () => {
    expect(referencedMatchNum("W101")).toBe(101);
    expect(referencedMatchNum("L102")).toBe(102);
  });

  it("renvoie null hors placeholder", () => {
    expect(referencedMatchNum(null)).toBeNull();
    expect(referencedMatchNum("")).toBeNull();
  });
});

describe("feedingMatches", () => {
  it("retrouve les deux demies qui alimentent la finale", () => {
    const semi1 = match({ id: 101, num: 101, phase: "semi_final" });
    const semi2 = match({ id: 102, num: 102, phase: "semi_final" });
    const final = match({ id: 104, num: 104, home_placeholder: "W101", away_placeholder: "W102" });

    const byNum = indexByNum([semi1, semi2, final]);
    const feeding = feedingMatches(final, byNum);

    expect(feeding.home?.id).toBe(101);
    expect(feeding.away?.id).toBe(102);
  });

  it("renvoie null quand la demie référencée est absente", () => {
    const final = match({ id: 104, num: 104, home_placeholder: "W901", away_placeholder: "W902" });
    const feeding = feedingMatches(final, indexByNum([final]));
    expect(feeding.home).toBeNull();
    expect(feeding.away).toBeNull();
  });
});
