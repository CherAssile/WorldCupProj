import { describe, expect, it } from "vitest";
import { aiPointsBreakdownLabel, pointsBreakdownLabel } from "./pointsBreakdown";

describe("pointsBreakdownLabel", () => {
  it("score exact + bon qualifié, non doublé", () => {
    expect(
      pointsBreakdownLabel({ scorePoints: 3, qualifierPoints: 2, doubled: false, phase: "round_of_16", total: 5, isKnockout: true })
    ).toBe("3 pts (score exact) + 2 pts (bon qualifié) = 5 pts");
  });

  it("même composition, doublée en demi-finale", () => {
    expect(
      pointsBreakdownLabel({ scorePoints: 3, qualifierPoints: 2, doubled: true, phase: "semi_final", total: 10, isKnockout: true })
    ).toBe("(3 pts (score exact) + 2 pts (bon qualifié)) × 2 (demi-finale) = 10 pts");
  });

  it("match de groupe : pas de volet qualifié", () => {
    expect(
      pointsBreakdownLabel({ scorePoints: 1, qualifierPoints: null, doubled: false, phase: "group", total: 1, isKnockout: false })
    ).toBe("1 pt (issue correcte) = 1 pt");
  });

  it("tout raté", () => {
    expect(
      pointsBreakdownLabel({ scorePoints: 0, qualifierPoints: 0, doubled: false, phase: "round_of_16", total: 0, isKnockout: true })
    ).toBe("0 pt (score raté) + 0 pt (qualifié raté) = 0 pts");
  });
});

describe("aiPointsBreakdownLabel", () => {
  it("jamais de volet qualifié, doublé en finale", () => {
    expect(aiPointsBreakdownLabel({ scorePoints: 3, doubled: true, phase: "final", total: 6 })).toBe(
      "3 pts (score exact) × 2 (finale) = 6 pts"
    );
  });

  it("non doublé", () => {
    expect(aiPointsBreakdownLabel({ scorePoints: 1, doubled: false, phase: "group", total: 1 })).toBe(
      "1 pt (issue correcte) = 1 pt"
    );
  });
});
