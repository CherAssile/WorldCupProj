export interface BracketMatchTeam {
  id: number;
  name: string;
  fifaCode: string;
  flagUrl: string | null;
}

interface BracketTeamRowProps {
  team: BracketMatchTeam | null;
  placeholderLabel: string | null;
  score: number | null;
  isWinner: boolean;
  isFinished: boolean;
}

function BracketTeamRow({ team, placeholderLabel, score, isWinner, isFinished }: BracketTeamRowProps) {
  const nameClass =
    isFinished && !isWinner ? "text-ink-secondary" : isWinner ? "font-extrabold text-ink" : "text-ink";

  return (
    <div className="flex items-center gap-2.5 px-3 py-2">
      {team ? (
        team.flagUrl ? (
          <img src={team.flagUrl} alt="" className="h-5 w-5 flex-shrink-0 rounded-full object-cover" />
        ) : (
          <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-elevated text-[9px] font-extrabold text-ink-secondary">
            {team.fifaCode}
          </div>
        )
      ) : (
        <div className="h-5 w-5 flex-shrink-0 rounded-full border border-dashed border-line" />
      )}
      <span className={`min-w-0 flex-1 truncate text-[13px] font-semibold ${nameClass}`}>
        {team ? team.name : (placeholderLabel ?? "À déterminer")}
      </span>
      {isFinished && score !== null ? (
        <span className={`num flex-shrink-0 text-[13px] font-extrabold ${isWinner ? "text-primary-light" : "text-ink-secondary"}`}>
          {score}
        </span>
      ) : null}
    </div>
  );
}

interface BracketMatchCardProps {
  metaLabel: string;
  homeTeam: BracketMatchTeam | null;
  awayTeam: BracketMatchTeam | null;
  homePlaceholderLabel: string | null;
  awayPlaceholderLabel: string | null;
  homeScore: number | null;
  awayScore: number | null;
  isFinished: boolean;
  winnerTeamId: number | null;
}

/** Noeud du bracket : une carte compacte à deux lignes (domicile/extérieur), purement présentationnel. */
export function BracketMatchCard({
  metaLabel,
  homeTeam,
  awayTeam,
  homePlaceholderLabel,
  awayPlaceholderLabel,
  homeScore,
  awayScore,
  isFinished,
  winnerTeamId,
}: BracketMatchCardProps) {
  return (
    <div className="w-full min-w-[200px] overflow-hidden rounded-2xl border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] shadow-[0_10px_24px_rgba(0,0,0,0.3)]">
      <div className="px-3 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-secondary">
        {metaLabel}
      </div>
      <div className="divide-y divide-white/[0.06] border-t border-white/[0.06]">
        <BracketTeamRow
          team={homeTeam}
          placeholderLabel={homePlaceholderLabel}
          score={homeScore}
          isWinner={homeTeam !== null && homeTeam.id === winnerTeamId}
          isFinished={isFinished}
        />
        <BracketTeamRow
          team={awayTeam}
          placeholderLabel={awayPlaceholderLabel}
          score={awayScore}
          isWinner={awayTeam !== null && awayTeam.id === winnerTeamId}
          isFinished={isFinished}
        />
      </div>
    </div>
  );
}
