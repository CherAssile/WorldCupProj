import { PredictionMatchCard } from "./PredictionMatchCard";
import { AiPickCard } from "./ui";
import { useAiPrediction } from "../hooks/useAiPrediction";
import { feedingMatches } from "../lib/feedingMatches";
import type { MatchPhase, MatchRead, PredictionRead } from "../types/api";

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

function teamsLine(match: MatchRead): string {
  const home = match.home_team?.name ?? match.home_placeholder_label ?? "À déterminer";
  const away = match.away_team?.name ?? match.away_placeholder_label ?? "À déterminer";
  return `${home} – ${away}`;
}

function FeedingRow({ match }: { match: MatchRead }) {
  const played = match.home_score !== null && match.away_score !== null;
  return (
    <div className="rounded-xl border border-line bg-[#0F1729] px-3.5 py-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-ink-muted">
          {PHASE_LABELS[match.phase]}
          {match.num !== null ? ` · match ${match.num}` : ""}
        </span>
        <span className="num text-[11px] text-ink-secondary">
          {DATE_FORMATTER.format(new Date(match.kickoff_at))}
        </span>
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="text-sm font-bold text-ink">{teamsLine(match)}</span>
        {played ? (
          <span className="num flex-shrink-0 text-sm font-extrabold text-ink">
            {match.home_score}–{match.away_score}
          </span>
        ) : null}
      </div>
    </div>
  );
}

interface SingleMatchPredictionProps {
  match: MatchRead;
  existingPrediction: PredictionRead | undefined;
  matchesByNum: Map<number, MatchRead>;
}

/**
 * Phase à un seul match (finale, petite finale) : la carte de pronostic élargie, plus un
 * panneau de contexte sur desktop — les deux matchs qui l'alimentent (avec leur date) et
 * le prono IA s'il existe. Sur mobile, seule la carte s'affiche (comportement inchangé).
 */
export function SingleMatchPrediction({ match, existingPrediction, matchesByNum }: SingleMatchPredictionProps) {
  const feeding = feedingMatches(match, matchesByNum);
  const aiPrediction = useAiPrediction(match.id);
  const hasFeeding = feeding.home !== null || feeding.away !== null;

  return (
    <div className="mx-auto max-w-[440px] min-[900px]:max-w-[960px]">
      <div className="grid grid-cols-1 gap-4 min-[900px]:grid-cols-[1.25fr_0.85fr] min-[900px]:items-start">
        <PredictionMatchCard match={match} existingPrediction={existingPrediction} />

        <aside className="hidden flex-col gap-3 min-[900px]:flex">
          {hasFeeding ? (
            <div className="rounded-2xl border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] p-5">
              <div className="text-xs font-bold uppercase tracking-[0.1em] text-ink-secondary">
                D'où vient ce match
              </div>
              <div className="mt-3 flex flex-col gap-2.5">
                {feeding.home ? <FeedingRow match={feeding.home} /> : null}
                {feeding.away ? <FeedingRow match={feeding.away} /> : null}
              </div>
            </div>
          ) : null}

          {aiPrediction.isSuccess ? (
            <AiPickCard
              homeTeamName={match.home_team?.name ?? match.home_placeholder_label_short ?? "Domicile"}
              awayTeamName={match.away_team?.name ?? match.away_placeholder_label_short ?? "Extérieur"}
              homeScore={aiPrediction.data.predicted_home_score}
              awayScore={aiPrediction.data.predicted_away_score}
              isFallback={aiPrediction.data.is_fallback}
            />
          ) : null}
        </aside>
      </div>
    </div>
  );
}
