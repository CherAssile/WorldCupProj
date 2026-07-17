import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MatchPhaseGroup } from "../types/api";

export function useMatches() {
  return useQuery({
    queryKey: ["matches"],
    queryFn: () => api.get<MatchPhaseGroup[]>("/matches"),
  });
}
