import { useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { useAuth } from "../context/AuthContext";
import { LeaderboardRow, type LeaderboardPlayer } from "../components/ui";
import { useLeaderboard } from "../hooks/useLeaderboard";
import type { LeaderboardEntryRead } from "../types/api";

type LeaderboardFilter = "general" | "matchday";

function getInitials(username: string): string {
  const parts = username.split(/[\s_\-.]+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return username.slice(0, 2).toUpperCase();
}

function toPlayer(entry: LeaderboardEntryRead): LeaderboardPlayer {
  return {
    rank: entry.rank,
    name: entry.username,
    initials: getInitials(entry.username),
    points: entry.total_points,
    exactScores: entry.exact_scores_count,
    isAI: entry.is_ai,
  };
}

function LoadingState() {
  return (
    <div className="flex flex-1 items-center justify-center px-5 py-16 text-sm text-ink-secondary">
      Chargement du classement…
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-16 text-center">
      <p className="text-sm text-danger">{message}</p>
      <button onClick={onRetry} className="rounded-2xl border border-line px-5 py-2.5 text-sm font-bold text-ink-body">
        Réessayer
      </button>
    </div>
  );
}

export function Classement() {
  const [filter, setFilter] = useState<LeaderboardFilter>("general");
  const { user } = useAuth();
  const leaderboardQuery = useLeaderboard();

  const entries = leaderboardQuery.data ?? [];
  const players = entries.map(toPlayer);
  const you = user ? entries.find((entry) => entry.user_id === user.id) : undefined;
  const youPlayer = you ? toPlayer(you) : null;

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={128} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col md:max-w-[860px]">
        <header className="px-5 pb-3.5 pt-4 md:flex md:items-end md:justify-between md:border-b md:border-white/[0.08] md:px-10 md:pb-[26px] md:pt-[34px]">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
              Classement global · {entries.length} joueur{entries.length > 1 ? "s" : ""}
            </div>
            <h1 className="mt-[3px] text-[30px] font-extrabold tracking-tight md:mt-1.5 md:text-[34px]">
              <span className="md:hidden">Classement</span>
              <span className="hidden md:inline">Classement général</span>
            </h1>
          </div>
          <div className="mt-4 hidden gap-2.5 md:flex">
            <button
              onClick={() => setFilter("general")}
              className={`rounded-xl px-[18px] py-2.5 text-[13px] font-bold transition-colors ${
                filter === "general" ? "bg-primary text-[#06210F]" : "border border-line text-ink-secondary"
              }`}
            >
              Général
            </button>
            <button
              onClick={() => setFilter("matchday")}
              className={`rounded-xl px-[18px] py-2.5 text-[13px] font-semibold transition-colors ${
                filter === "matchday" ? "bg-primary text-[#06210F]" : "border border-line text-ink-secondary"
              }`}
            >
              Cette journée
            </button>
          </div>
        </header>

        {leaderboardQuery.isLoading ? <LoadingState /> : null}

        {leaderboardQuery.isError ? (
          <ErrorState
            message="Impossible de charger le classement. Vérifie ta connexion et réessaie."
            onRetry={() => leaderboardQuery.refetch()}
          />
        ) : null}

        {leaderboardQuery.isSuccess && entries.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-5 py-16 text-center text-sm text-ink-secondary">
            Le classement n'est pas encore disponible — reviens après les premiers résultats.
          </div>
        ) : null}

        {leaderboardQuery.isSuccess && entries.length > 0 ? (
          <>
            <div className="hidden grid-cols-[64px_1fr_200px_130px] gap-4 px-10 py-3.5 text-[11px] font-bold uppercase tracking-[0.1em] text-ink-secondary md:grid">
              <span>Rang</span>
              <span>Joueur</span>
              <span className="text-right">Scores exacts</span>
              <span className="text-right">Points</span>
            </div>

            <main className="flex-1 overflow-y-auto px-4 pb-3 pt-1 md:px-6 md:pb-2 md:pt-0">
              {players.map((player) => (
                <LeaderboardRow key={player.rank} player={player} highlighted={player.rank === youPlayer?.rank} />
              ))}
            </main>
          </>
        ) : null}

        {leaderboardQuery.isSuccess && youPlayer ? (
          <div className="sticky bottom-0 border-t border-white/[0.09] bg-[#0D1424]">
            <div className="px-4 pb-3 pt-3 md:px-6 md:pb-[26px] md:pt-[14px]">
              <div className="mb-2 pl-1 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-secondary md:pl-4">
                Votre position
              </div>
              <LeaderboardRow player={youPlayer} highlighted />
            </div>
            <div className="md:hidden">
              <AppBottomNav />
            </div>
          </div>
        ) : (
          <div className="sticky bottom-0 md:hidden">
            <AppBottomNav />
          </div>
        )}
      </div>
    </div>
  );
}
