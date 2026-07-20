import { useNavigate } from "react-router-dom";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import {
  AiPickCard,
  ErrorState,
  LoadingState,
  NextMatchHero,
  RankTile,
  TotalPointsBadge,
  TrainingTile,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useAiPrediction } from "../hooks/useAiPrediction";
import { useMatches } from "../hooks/useMatches";
import { useMyLeaderboardEntry } from "../hooks/useMyLeaderboardEntry";
import { getInitials } from "../lib/initials";
import { findNextMatch } from "../lib/nextMatch";
import { frenchTeamName } from "../lib/teamNamesFr";
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

const KICKOFF_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Bonjour,";
  if (hour < 18) return "Bon après-midi,";
  return "Bonsoir,";
}

export function Accueil() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const leaderboard = useMyLeaderboardEntry();
  const matchesQuery = useMatches();

  const nextMatch = matchesQuery.isSuccess ? findNextMatch(matchesQuery.data) : null;
  const aiPredictionQuery = useAiPrediction(nextMatch?.id ?? null);

  const points = leaderboard.entry?.total_points ?? 0;
  const initials = user ? getInitials(user.username) : undefined;

  const aiPick =
    aiPredictionQuery.isSuccess && nextMatch?.home_team && nextMatch?.away_team ? (
      <AiPickCard
        homeTeamName={frenchTeamName(nextMatch.home_team.name)}
        awayTeamName={frenchTeamName(nextMatch.away_team.name)}
        homeScore={aiPredictionQuery.data.predicted_home_score}
        awayScore={aiPredictionQuery.data.predicted_away_score}
        isFallback={aiPredictionQuery.data.is_fallback}
      />
    ) : null;

  return (
    <div className="min-h-screen bg-app">
      <AppTopNav points={points} userInitials={initials} />

      <div className="mx-auto max-w-[440px] md:max-w-[1040px]">
        <header className="flex items-center justify-between px-5 pb-1 pt-4 md:hidden">
          <div>
            <div className="text-[13px] text-ink-secondary">{greeting()}</div>
            <div className="text-2xl font-extrabold tracking-tight">{user?.username ?? ""}</div>
          </div>
          <div className="flex items-center gap-2.5">
            <TotalPointsBadge points={points} />
            <button
              onClick={logout}
              title="Se déconnecter"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-ink-secondary"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="M16 17l5-5-5-5M21 12H9" />
              </svg>
            </button>
          </div>
        </header>
        <header className="hidden px-8 pb-0 pt-7 md:block">
          <div className="text-sm text-ink-secondary">{greeting()}</div>
          <h1 className="mt-0.5 text-[30px] font-extrabold tracking-tight">{user?.username ?? ""}</h1>
        </header>

        <div className="px-5 pb-2 pt-4 md:grid md:grid-cols-[1.7fr_1fr] md:gap-5 md:px-8 md:pb-9 md:pt-[22px]">
          {matchesQuery.isLoading ? (
            <LoadingState message="Chargement du prochain match…" />
          ) : matchesQuery.isError ? (
            <ErrorState
              message="Impossible de charger le prochain match. Vérifie ta connexion et réessaie."
              onRetry={() => matchesQuery.refetch()}
            />
          ) : nextMatch ? (
            <NextMatchHero
              groupLabel={`Prochain match · ${PHASE_LABELS[nextMatch.phase]}`}
              kickoffLabel={KICKOFF_FORMATTER.format(new Date(nextMatch.kickoff_at))}
              homeTeam={{
                name: (nextMatch.home_team ? frenchTeamName(nextMatch.home_team.name) : null) ?? nextMatch.home_placeholder_label ?? "À déterminer",
                fifaCode: nextMatch.home_team?.fifa_code ?? "?",
                flagUrl: nextMatch.home_team?.flag_url ?? null,
              }}
              awayTeam={{
                name: (nextMatch.away_team ? frenchTeamName(nextMatch.away_team.name) : null) ?? nextMatch.away_placeholder_label ?? "À déterminer",
                fifaCode: nextMatch.away_team?.fifa_code ?? "?",
                flagUrl: nextMatch.away_team?.flag_url ?? null,
              }}
              countdownTarget={new Date(nextMatch.kickoff_at)}
              onPredict={() => navigate("/pronostics")}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center px-5 py-16 text-center text-sm text-ink-secondary">
              Aucun match à pronostiquer pour le moment.
            </div>
          )}

          <div className="mt-3.5 grid grid-cols-2 gap-3 md:mt-0 md:flex md:flex-col md:gap-4">
            {leaderboard.isLoading ? (
              <LoadingState message="Chargement du rang…" />
            ) : leaderboard.isError ? (
              <ErrorState message="Impossible de charger ton rang." onRetry={() => leaderboard.refetch()} />
            ) : leaderboard.entry ? (
              <RankTile rank={leaderboard.entry.rank} totalPlayers={leaderboard.data?.length ?? 0} />
            ) : (
              <div className="flex flex-col justify-center rounded-[18px] border border-white/[0.06] bg-surface p-4 text-center text-xs text-ink-secondary md:rounded-[20px] md:p-5">
                Pas encore classé — pronostique un match pour apparaître au classement.
              </div>
            )}

            <TrainingTile record="Nouveau duel" onClick={() => navigate("/entrainement")} />

            {aiPick ? <div className="col-span-2 hidden md:flex">{aiPick}</div> : null}
          </div>
        </div>

        {aiPick ? <div className="px-5 pb-8 md:hidden">{aiPick}</div> : null}
      </div>

      <div className="md:hidden">
        <AppBottomNav />
      </div>
    </div>
  );
}
