import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { UserCreate, UserRead } from "../types/api";

/** POST /auth/register crée le compte mais ne renvoie pas de jeton — un login suit derrière. */
export function useRegister() {
  return useMutation({
    mutationFn: (body: UserCreate) => api.post<UserRead>("/auth/register", body),
  });
}
