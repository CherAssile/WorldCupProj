import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Token } from "../types/api";

interface LoginInput {
  email: string;
  password: string;
}

/** POST /auth/login attend OAuth2PasswordRequestForm : le champ s'appelle "username" mais reçoit l'email. */
export function useLogin() {
  return useMutation({
    mutationFn: ({ email, password }: LoginInput) =>
      api.postForm<Token>("/auth/login", { username: email, password }),
  });
}
