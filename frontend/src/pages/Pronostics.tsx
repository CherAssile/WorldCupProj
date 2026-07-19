import { useEffect, useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { PredictionMatchCard } from "../components/PredictionMatchCard";
import { SingleMatchPrediction } from "../components/SingleMatchPrediction";
import { ErrorState, LoadingState, PhaseTabs, TotalPointsBadge, type PhaseTabDef } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useMatches } from "../hooks/useMatches";
import { useMyLeaderboardEntry } from "../hooks/useMyLeaderboardEntry";
import { usePredictions } from "../hooks/usePredictions";
import { indexByNum } from "../lib/feedingMatches";
import { getInitials } from "../lib/initials";
import type { MatchPhase } from "../types/api";

const PHASE_LABELS: Record<MatchPhase, string> = {
  group: "Groupes",
  round_of_32: "32es",
  round_of_16: "8es",
  quarter_final: "Quarts",
  semi_final: "Demies",
  third_place: "Petite finale",
  final: "Finale",
};

export function Pronostics() {
  const { user } = useAuth();
  const leaderboard = useMyLeaderboardEntry();
  const matchesQuery = useMatches();
  const predictionsQuery = usePredictions();
  const [activePhase, setActivePhase] = useState<MatchPhase | null>(null);

  const points = leaderboard.entry?.total_points ?? 0;

  const groups = matchesQuery.data ?? [];

  useEffect(() => {
    if (activePhase === null && groups.length > 0) {
      setActivePhase(groups[0].phase);
    }
  }, [groups, activePhase]);

  const tabs: PhaseTabDef<MatchPhase>[] = groups.map((group) => ({
    id: group.phase,
    label: PHASE_LABELS[group.phase],
  }));

  const activeGroup = groups.find((group) => group.phase === activePhase) ?? groups[0];

  const predictionsByMatchId = new Map((predictionsQuery.data ?? []).map((prediction) => [prediction.match_id, prediction]));
  const matchesByNum = indexByNum(groups.flatMap((group) => group.matches));
  const isSinglePhase = (activeGroup?.matches.length ?? 0) === 1;

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={points} userInitials={user ? getInitials(user.username) : undefined} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col min-[900px]:max-w-[1440px]">
        <header className="flex items-start justify-between px-5 pb-1 pt-4 min-[900px]:px-8 min-[900px]:pt-8">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Coupe du monde 2026</div>
            <h1 className="mt-[3px] text-[30px] font-extrabold tracking-tight">Pronostics</h1>
          </div>
          <TotalPointsBadge points={points} />
        </header>

        {matchesQuery.isLoading ? <LoadingState message="Chargement des matchs…" /> : null}

        {matchesQuery.isError ? (
          <ErrorState
            message="Impossible de charger les matchs. Vérifie ta connexion et réessaie."
            onRetry={() => matchesQuery.refetch()}
          />
        ) : null}

        {matchesQuery.isSuccess && activeGroup ? (
          <>
            <div className="px-5 pb-4 pt-[18px] min-[900px]:px-8">
              <PhaseTabs tabs={tabs} value={activeGroup.phase} onChange={setActivePhase} />
            </div>

            <main className="flex-1 px-5 pb-6 min-[900px]:px-8">
              {predictionsQuery.isError ? (
                <div className="mb-3.5 rounded-2xl border border-danger/[0.3] bg-danger/[0.1] px-4 py-3 text-xs text-danger">
                  Impossible de charger tes pronostics existants — les champs peuvent apparaître vides même si tu as
                  déjà pronostiqué.
                </div>
              ) : null}

              {isSinglePhase ? (
                <SingleMatchPrediction
                  match={activeGroup.matches[0]}
                  existingPrediction={predictionsByMatchId.get(activeGroup.matches[0].id)}
                  matchesByNum={matchesByNum}
                />
              ) : (
                <div className="grid grid-cols-1 gap-3.5 min-[900px]:grid-cols-2 min-[900px]:gap-5 min-[1400px]:grid-cols-3">
                  {activeGroup.matches.map((match) => (
                    <PredictionMatchCard
                      key={match.id}
                      match={match}
                      existingPrediction={predictionsByMatchId.get(match.id)}
                    />
                  ))}
                </div>
              )}
            </main>
          </>
        ) : null}

        {matchesQuery.isSuccess && groups.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-5 py-16 text-center text-sm text-ink-secondary">
            Aucun match disponible pour le moment.
          </div>
        ) : null}
      </div>

      <div className="sticky bottom-0 md:hidden">
        <AppBottomNav />
      </div>
    </div>
  );
}
