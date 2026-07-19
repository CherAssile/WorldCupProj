import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Message } from "../types/api";

/** Demande de réinitialisation. Le serveur répond toujours 200 avec le même message,
 * e-mail connu ou non (anti-énumération) : pas de cas « e-mail introuvable » à gérer. */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => api.post<Message>("/auth/forgot-password", { email }),
  });
}
