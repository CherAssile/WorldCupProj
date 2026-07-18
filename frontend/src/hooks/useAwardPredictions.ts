import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { AwardPredictionRead } from "../types/api";

export function useAwardPredictions() {
  return useQuery({
    queryKey: ["award-predictions", "me"],
    queryFn: () => api.get<AwardPredictionRead[]>("/award-predictions/me"),
  });
}
