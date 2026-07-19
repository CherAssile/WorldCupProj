import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Message } from "../types/api";

interface ResetPasswordInput {
  token: string;
  newPassword: string;
}

/** Consomme le jeton du lien e-mail et remplace le mot de passe. 400 si invalide/expiré/déjà utilisé. */
export function useResetPassword() {
  return useMutation({
    mutationFn: ({ token, newPassword }: ResetPasswordInput) =>
      api.post<Message>("/auth/reset-password", { token, new_password: newPassword }),
  });
}
