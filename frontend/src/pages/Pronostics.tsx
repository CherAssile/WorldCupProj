import { useEffect, useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { PredictionMatchCard } from "../components/PredictionMatchCard";
import { PhaseTabs, TotalPointsBadge, type PhaseTabDef } from "../components/ui";
import { useMatches } from "../hooks/useMatches";
import { usePredictions } from "../hooks/usePredictions";
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

function LoadingState() {
  return (
    <div className="flex flex-1 items-center justify-center px-5 py-16 text-sm text-ink-secondary">
      Chargement des matchs…
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-16 text-center">
      <p className="text-sm text-danger">{message}</p>
      <button
        onClick={onRetry}
        className="rounded-2xl border border-line px-5 py-2.5 text-sm font-bold text-ink-body"
      >
        Réessayer
      </button>
    </div>
  );
}

export function Pronostics() {
  const matchesQuery = useMatches();
  const predictionsQuery = usePredictions();
  const [activePhase, setActivePhase] = useState<MatchPhase | null>(null);

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

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={128} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col">
        <header className="flex items-start justify-between px-5 pb-1 pt-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Coupe du monde 2026</div>
            <h1 className="mt-[3px] text-[30px] font-extrabold tracking-tight">Pronostics</h1>
          </div>
          <TotalPointsBadge points={128} />
        </header>

        {matchesQuery.isLoading ? <LoadingState /> : null}

        {matchesQuery.isError ? (
          <ErrorState
            message="Impossible de charger les matchs. Vérifie ta connexion et réessaie."
            onRetry={() => matchesQuery.refetch()}
          />
        ) : null}

        {matchesQuery.isSuccess && activeGroup ? (
          <>
            <div className="px-5 pb-4 pt-[18px]">
              <PhaseTabs tabs={tabs} value={activeGroup.phase} onChange={setActivePhase} />
            </div>

            <main className="flex-1 px-5 pb-6">
              {predictionsQuery.isError ? (
                <div className="mb-3.5 rounded-2xl border border-danger/[0.3] bg-danger/[0.1] px-4 py-3 text-xs text-danger">
                  Impossible de charger tes pronostics existants — les champs peuvent apparaître vides même si tu as
                  déjà pronostiqué.
                </div>
              ) : null}

              <div className="flex flex-col gap-3.5">
                {activeGroup.matches.map((match) => (
                  <PredictionMatchCard
                    key={match.id}
                    match={match}
                    existingPrediction={predictionsByMatchId.get(match.id)}
                  />
                ))}
              </div>
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
