import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { AwardRead } from "../types/api";

export function useAwards() {
  return useQuery({
    queryKey: ["awards"],
    queryFn: () => api.get<AwardRead[]>("/awards"),
  });
}
