import { describe, expect, it } from "vitest";
import { api } from "./api";
import type { MatchPhaseGroup } from "../types/api";

// Test d'intégration : suppose le backend démarré (docker compose up) et joignable
// via VITE_API_URL (voir .env à la racine du repo). Vérifie que le client centralisé
// (base URL, headers, parsing JSON) fonctionne réellement, pas seulement en théorie.
describe("api client", () => {
  it("GET /matches renvoie des données depuis le backend", async () => {
    const groups = await api.get<MatchPhaseGroup[]>("/matches");

    expect(Array.isArray(groups)).toBe(true);
    if (groups.length > 0) {
      expect(groups[0]).toHaveProperty("phase");
      expect(groups[0]).toHaveProperty("matches");
    }
  });
});
