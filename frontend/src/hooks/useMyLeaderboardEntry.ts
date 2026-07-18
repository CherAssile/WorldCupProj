import { useAuth } from "../context/AuthContext";
import { useLeaderboard } from "./useLeaderboard";

/**
 * Retrouve la ligne de classement de l'utilisateur connecté. /leaderboard ne distingue
 * pas "moi" côté serveur : on croise la liste complète avec l'id de l'utilisateur courant.
 */
export function useMyLeaderboardEntry() {
  const { user } = useAuth();
  const leaderboardQuery = useLeaderboard();
  const entry = user ? leaderboardQuery.data?.find((candidate) => candidate.user_id === user.id) : undefined;

  return { ...leaderboardQuery, entry };
}
