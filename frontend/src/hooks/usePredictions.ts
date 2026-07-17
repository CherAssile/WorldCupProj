import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { PredictionRead } from "../types/api";

export function usePredictions() {
  return useQuery({
    queryKey: ["predictions", "me"],
    queryFn: () => api.get<PredictionRead[]>("/predictions/me"),
  });
}
