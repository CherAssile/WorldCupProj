import { useEffect, useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { BracketMatchCard, ErrorState, LoadingState, PhaseTabs, type BracketMatchTeam, type PhaseTabDef } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useMatches } from "../hooks/useMatches";
import { useMyLeaderboardEntry } from "../hooks/useMyLeaderboardEntry";
import { sortBracketMatches } from "../lib/bracket";
import { getInitials } from "../lib/initials";
import type { MatchPhase, MatchPhaseGroup, MatchRead } from "../types/api";

const PHASE_LABELS: Record<MatchPhase, string> = {
  group: "Groupes",
  round_of_32: "32es",
  round_of_16: "8es",
  quarter_final: "Quarts",
  semi_final: "Demies",
  third_place: "Petite finale",
  final: "Finale",
};

const KICKOFF_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function toBracketTeam(team: MatchRead["home_team"]): BracketMatchTeam | null {
  if (!team) return null;
  return { id: team.id, name: team.name, fifaCode: team.fifa_code, flagUrl: team.flag_url };
}

function metaLabel(match: MatchRead): string {
  if (match.status === "finished") return "Terminé";
  if (match.status === "live") return "● En direct";
  return `Coup d'envoi · ${KICKOFF_FORMATTER.format(new Date(match.kickoff_at))}`;
}

function BracketMatchNode({ match }: { match: MatchRead }) {
  return (
    <BracketMatchCard
      metaLabel={metaLabel(match)}
      homeTeam={toBracketTeam(match.home_team)}
      awayTeam={toBracketTeam(match.away_team)}
      homePlaceholderLabel={match.home_placeholder_label_short}
      awayPlaceholderLabel={match.away_placeholder_label_short}
      homeScore={match.home_score}
      awayScore={match.away_score}
      isFinished={match.status === "finished"}
      winnerTeamId={match.winner_team?.id ?? null}
    />
  );
}

export function Bracket() {
  const { user } = useAuth();
  const leaderboard = useMyLeaderboardEntry();
  const matchesQuery = useMatches();
  const [activePhase, setActivePhase] = useState<MatchPhase | null>(null);

  const groups: MatchPhaseGroup[] = matchesQuery.data ?? [];
  const knockoutGroups = groups.filter((group) => group.phase !== "group" && group.matches.length > 0);

  useEffect(() => {
    if (activePhase === null && knockoutGroups.length > 0) {
      setActivePhase(knockoutGroups[0].phase);
    }
  }, [knockoutGroups, activePhase]);

  const tabs: PhaseTabDef<MatchPhase>[] = knockoutGroups.map((group) => ({
    id: group.phase,
    label: PHASE_LABELS[group.phase],
  }));
  const activeGroup = knockoutGroups.find((group) => group.phase === activePhase) ?? knockoutGroups[0];

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={leaderboard.entry?.total_points ?? 0} userInitials={user ? getInitials(user.username) : undefined} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col md:max-w-none">
        <header className="px-5 pb-1 pt-4 md:border-b md:border-white/[0.08] md:px-10 md:pb-6 md:pt-8">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Coupe du monde 2026</div>
          <h1 className="mt-[3px] text-[27px] font-extrabold tracking-tight md:text-[32px]">Phases finales</h1>
        </header>

        {matchesQuery.isLoading ? <LoadingState message="Chargement du bracket…" /> : null}

        {matchesQuery.isError ? (
          <ErrorState
            message="Impossible de charger le bracket. Vérifie ta connexion et réessaie."
            onRetry={() => matchesQuery.refetch()}
          />
        ) : null}

        {matchesQuery.isSuccess && knockoutGroups.length === 0 ? (
          <div className="flex flex-1 items-center justify-center px-5 py-16 text-center text-sm text-ink-secondary">
            Aucun match de phase finale disponible pour le moment.
          </div>
        ) : null}

        {matchesQuery.isSuccess && activeGroup ? (
          <>
            <div className="px-5 pb-4 pt-[18px] md:hidden">
              <PhaseTabs tabs={tabs} value={activeGroup.phase} onChange={setActivePhase} />
            </div>
            <main className="flex-1 px-5 pb-6 md:hidden">
              <div className="flex flex-col gap-3.5">
                {sortBracketMatches(activeGroup.matches).map((match) => (
                  <BracketMatchNode key={match.id} match={match} />
                ))}
              </div>
            </main>

            <main className="hidden flex-1 overflow-x-auto px-10 py-8 md:block">
              <div className="flex min-w-max gap-6">
                {knockoutGroups.map((group) => (
                  <div key={group.phase} className="flex w-[220px] flex-shrink-0 flex-col gap-5">
                    <div className="text-xs font-bold uppercase tracking-[0.1em] text-ink-secondary">
                      {PHASE_LABELS[group.phase]}
                    </div>
                    <div className="flex flex-1 flex-col justify-around gap-5">
                      {sortBracketMatches(group.matches).map((match) => (
                        <BracketMatchNode key={match.id} match={match} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </main>
          </>
        ) : null}
      </div>

      <div className="sticky bottom-0 md:hidden">
        <AppBottomNav />
      </div>
    </div>
  );
}
