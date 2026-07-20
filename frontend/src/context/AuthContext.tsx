import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, UNAUTHORIZED_EVENT } from "../lib/api";
import { clearToken, getToken, setToken as persistToken } from "../lib/auth";
import type { UserRead } from "../types/api";

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  user: UserRead | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getToken());
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.get<UserRead>("/auth/me"),
    enabled: token !== null,
    staleTime: 5 * 60_000,
  });

  const login = useCallback((newToken: string) => {
    persistToken(newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setToken(null);
    queryClient.clear();
  }, [queryClient]);

  // Jeton expiré/invalide détecté par le client API (401 sur une requête authentifiée) :
  // déconnecte pour que ProtectedRoute redirige vers /connexion, plutôt que de laisser
  // chaque écran afficher une bannière d'erreur réseau pour une session expirée.
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout);
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{ token, isAuthenticated: token !== null, user: meQuery.data ?? null, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé sous un AuthProvider");
  }
  return context;
}
