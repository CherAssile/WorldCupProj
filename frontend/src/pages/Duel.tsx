import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { ErrorState, FinishedMatchDuelCard, LoadingState, type MatchTeamInfo } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useMyDuel } from "../hooks/useMyDuel";
import { useMyLeaderboardEntry } from "../hooks/useMyLeaderboardEntry";
import { buildDuelCardSides } from "../lib/duelCard";
import { getInitials } from "../lib/initials";
import { frenchTeamName } from "../lib/teamNamesFr";
import type { MatchDuelRead, MatchPhase } from "../types/api";

const PHASE_LABELS: Record<MatchPhase, string> = {
  group: "Groupes",
  round_of_32: "32es",
  round_of_16: "8es",
  quarter_final: "Quarts",
  semi_final: "Demies",
  third_place: "Petite finale",
  final: "Finale",
};

const DATE_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function toTeamInfo(team: MatchDuelRead["home_team"]): MatchTeamInfo | null {
  if (!team) return null;
  return { name: frenchTeamName(team.name), fifaCode: team.fifa_code, flagUrl: team.flag_url };
}

/** Détail du duel joueur/IA en mode compétitif : totaux cumulés puis l'historique de
 * chaque manche (match terminé), du plus récent au plus ancien. Lecture seule des mêmes
 * données que le classement général (predictions, ai_predictions) — n'affecte jamais le
 * classement, qui reste global et unique. */
export function Duel() {
  const { user } = useAuth();
  const leaderboard = useMyLeaderboardEntry();
  const duelQuery = useMyDuel();

  const points = leaderboard.entry?.total_points ?? 0;
  const initials = user ? getInitials(user.username) : undefined;

  return (
    <div className="flex min-h-screen flex-col bg-app">
      <AppTopNav points={points} userInitials={initials} />

      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col md:max-w-[860px]">
        <header className="px-5 pb-1 pt-4 md:px-10 md:pb-6 md:pt-8">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Mode compétitif</div>
          <h1 className="mt-[3px] text-[27px] font-extrabold tracking-tight md:text-[32px]">Duel contre l'IA</h1>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-secondary md:text-sm">
            Une confrontation à part entière, à côté du classement général : chaque match déjà joué où vous avez
            tous les deux pronostiqué compte pour une manche.
          </p>
        </header>

        {duelQuery.isLoading ? <LoadingState message="Chargement du duel…" /> : null}

        {duelQuery.isError ? (
          <ErrorState
            message="Impossible de charger le duel. Vérifie ta connexion et réessaie."
            onRetry={() => duelQuery.refetch()}
          />
        ) : null}

        {duelQuery.isSuccess ? (
          <>
            <div className="mx-5 mb-5 rounded-2xl border border-white/[0.08] bg-elevated px-5 py-4 md:mx-10">
              <div className="num text-center text-3xl font-extrabold">
                Toi {duelQuery.data.user_total_points} – {duelQuery.data.ai_total_points} IA
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="num text-base font-bold text-primary-light">{duelQuery.data.matches_user_ahead}</div>
                  <div className="text-[11px] text-ink-secondary">gagnées</div>
                </div>
                <div>
                  <div className="num text-base font-bold text-ink">{duelQuery.data.matches_tied}</div>
                  <div className="text-[11px] text-ink-secondary">égalités</div>
                </div>
                <div>
                  <div className="num text-base font-bold text-ink-secondary">{duelQuery.data.matches_ai_ahead}</div>
                  <div className="text-[11px] text-ink-secondary">perdues</div>
                </div>
              </div>
            </div>

            <main className="flex-1 px-5 pb-6 md:px-10">
              {duelQuery.data.results.length === 0 ? (
                <div className="flex flex-1 items-center justify-center py-16 text-center text-sm text-ink-secondary">
                  Aucun match terminé pour le moment.
                </div>
              ) : (
                <div className="flex flex-col gap-3.5">
                  {[...duelQuery.data.results].reverse().map((entry) => {
                    const { user: userSide, ai } = buildDuelCardSides(entry);
                    return (
                      <FinishedMatchDuelCard
                        key={entry.match_id}
                        metaLabel={`${PHASE_LABELS[entry.phase]} · ${DATE_FORMATTER.format(new Date(entry.kickoff_at))}`}
                        homeTeam={toTeamInfo(entry.home_team)}
                        awayTeam={toTeamInfo(entry.away_team)}
                        homeScore={entry.home_score ?? 0}
                        awayScore={entry.away_score ?? 0}
                        duelStatus="ready"
                        user={userSide}
                        ai={ai}
                      />
                    );
                  })}
                </div>
              )}
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
