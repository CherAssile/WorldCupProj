import { useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { TrainingMatchSlot } from "../components/TrainingMatchSlot";
import { Button, ErrorState, LoadingState } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useCreateTrainingSession } from "../hooks/useCreateTrainingSession";
import { useMyLeaderboardEntry } from "../hooks/useMyLeaderboardEntry";
import { useTrainingSession } from "../hooks/useTrainingSession";
import { useTrainingSessionResults } from "../hooks/useTrainingSessionResults";
import { getInitials } from "../lib/initials";

function StartScreen({
  onStart,
  isStarting,
  error,
}: {
  onStart: () => void;
  isStarting: boolean;
  error: string | null;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-primary bg-[#0F1729]">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2CC169" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M12 8V4M9 4h6" />
          <circle cx="9" cy="14" r="1.2" fill="#2CC169" />
          <circle cx="15" cy="14" r="1.2" fill="#2CC169" />
        </svg>
      </div>
      <h2 className="text-xl font-extrabold">Défie l'IA</h2>
      <p className="max-w-[320px] text-sm text-ink-secondary">
        Pronostique des matchs déjà joués dont le résultat t'est caché. L'IA pronostique les mêmes matchs :
        comparez vos scores dès que ton prono est validé.
      </p>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      <Button variant="primary" onClick={onStart} disabled={isStarting}>
        {isStarting ? "Démarrage…" : "Commencer une session"}
      </Button>
    </div>
  );
}

export function Entrainement() {
  const { user } = useAuth();
  const leaderboard = useMyLeaderboardEntry();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const createSession = useCreateTrainingSession();
  const sessionQuery = useTrainingSession(sessionId);
  const resultsQuery = useTrainingSessionResults(sessionId);

  function handleStart() {
    createSession.mutate(
      {},
      {
        onSuccess: (data) => setSessionId(data.id),
      }
    );
  }

  const matches = sessionQuery.data ? [...sessionQuery.data.matches].sort((a, b) => a.position - b.position) : [];
  const resultsByMatchId = new Map((resultsQuery.data?.results ?? []).map((result) => [result.historical_match_id, result]));
  const completed = resultsQuery.data?.completed ?? false;

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={leaderboard.entry?.total_points ?? 0} userInitials={user ? getInitials(user.username) : undefined} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col md:max-w-[720px]">
        <header className="px-5 pb-1 pt-4 md:px-10 md:pb-6 md:pt-8">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Entraînement</div>
          <h1 className="mt-[3px] text-[27px] font-extrabold tracking-tight md:text-[32px]">Duel contre l'IA</h1>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-secondary md:text-sm">
            Hors classement — ce mode n'affecte jamais ton classement compétitif.
          </p>
        </header>

        {sessionId === null ? (
          <StartScreen
            onStart={handleStart}
            isStarting={createSession.isPending}
            error={createSession.isError ? createSession.error.message : null}
          />
        ) : sessionQuery.isLoading ? (
          <LoadingState message="Tirage des matchs…" />
        ) : sessionQuery.isError ? (
          <ErrorState
            message="Impossible de charger la session. Vérifie ta connexion et réessaie."
            onRetry={() => sessionQuery.refetch()}
          />
        ) : sessionQuery.isSuccess ? (
          <main className="flex-1 px-5 pb-8 md:px-10">
            <div className="mb-4 flex items-center justify-between rounded-2xl border border-white/[0.08] bg-elevated px-4 py-3">
              <span className="text-xs font-bold uppercase tracking-[0.08em] text-ink-secondary">Duel cumulé</span>
              <span className="num text-sm font-extrabold text-ink">
                Toi {resultsQuery.data?.user_total_points ?? 0} – {resultsQuery.data?.ai_total_points ?? 0} IA
              </span>
            </div>

            {resultsQuery.isError ? (
              <div className="mb-3.5 rounded-2xl border border-danger/[0.3] bg-danger/[0.1] px-4 py-3 text-xs text-danger">
                Impossible de charger le duel cumulé — tes pronos déjà validés restent enregistrés.
              </div>
            ) : null}

            <div className="flex flex-col gap-3.5">
              {matches.map((match, index) => (
                <TrainingMatchSlot
                  key={match.historical_match_id}
                  sessionId={sessionId}
                  match={match}
                  index={index}
                  total={matches.length}
                  result={resultsByMatchId.get(match.historical_match_id)}
                />
              ))}
            </div>

            {completed ? (
              <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl border border-primary/[0.3] bg-[linear-gradient(155deg,#173A2A,#122A1F)] p-5 text-center">
                <div className="text-sm font-bold text-primary-light">Session terminée</div>
                <div className="num text-2xl font-extrabold text-ink">
                  Toi {resultsQuery.data?.user_total_points} – {resultsQuery.data?.ai_total_points} IA
                </div>
                <Button variant="primary" size="sm" onClick={() => setSessionId(null)}>
                  Nouvelle session
                </Button>
              </div>
            ) : null}
          </main>
        ) : null}
      </div>

      <div className="sticky bottom-0 md:hidden">
        <AppBottomNav />
      </div>
    </div>
  );
}
