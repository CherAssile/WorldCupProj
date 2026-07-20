import type { MatchTeamInfo } from "./MatchPredictionCard";

function TeamBadge({ team }: { team: MatchTeamInfo | null }) {
  if (!team) {
    return (
      <div className="flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-full border border-dashed border-line text-ink-muted">
        ?
      </div>
    );
  }
  return team.flagUrl ? (
    <img src={team.flagUrl} alt="" className="h-[46px] w-[46px] flex-shrink-0 rounded-full object-cover shadow-[0_0_0_2px_rgba(255,255,255,0.12)]" />
  ) : (
    <div className="flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-full bg-elevated text-[11px] font-extrabold text-ink-secondary shadow-[0_0_0_2px_rgba(255,255,255,0.12)]">
      {team.fifaCode}
    </div>
  );
}

interface DuelRowProps {
  label: string;
  scoreLabel: string;
  breakdownLabel: string;
  points: number | null; // null = pas de pronostic
  isWinner: boolean;
  badge?: string; // ex. "repli" pour un prono IA de secours
}

function DuelRow({ label, scoreLabel, breakdownLabel, points, isWinner, badge }: DuelRowProps) {
  if (points === null) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-transparent px-3.5 py-2.5">
        <span className="text-xs font-bold uppercase tracking-[0.06em] text-ink-muted">{label}</span>
        <div className="mt-0.5 text-[13px] text-ink-muted">{breakdownLabel}</div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border px-3.5 py-2.5 ${
        isWinner ? "border-primary/[0.4] bg-primary/[0.12]" : "border-transparent bg-elevated"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.06em] ${isWinner ? "text-primary-light" : "text-ink-secondary"}`}>
          {label}
          {badge ? (
            <span className="rounded-full bg-ink-secondary/[0.15] px-1.5 py-[1px] text-[9px] font-bold normal-case tracking-normal text-ink-secondary">
              {badge}
            </span>
          ) : null}
        </span>
        <span className="num text-[15px] font-extrabold text-ink">{scoreLabel}</span>
        <span className={`num flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-extrabold ${isWinner ? "bg-primary text-[#06210F]" : "bg-[#0F1729] text-ink-secondary"}`}>
          +{points} pt{points !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="mt-1 text-[11px] text-ink-secondary">{breakdownLabel}</div>
    </div>
  );
}

interface FinishedMatchDuelCardProps {
  metaLabel: string;
  homeTeam: MatchTeamInfo | null;
  awayTeam: MatchTeamInfo | null;
  homePlaceholder?: string | null;
  awayPlaceholder?: string | null;
  homeScore: number;
  awayScore: number;

  /** Le score réel s'affiche toujours, indépendamment de ceci : le duel (points, IA) est
   * une section secondaire qui charge séparément (GET /me/duel-ia), sans jamais bloquer
   * ni fausser l'affichage du résultat. */
  duelStatus: "loading" | "error" | "ready";
  user: {
    scoreLabel: string;
    breakdownLabel: string;
    points: number;
  } | null; // null = pas pronostiqué (uniquement pertinent si duelStatus === "ready")

  ai: {
    scoreLabel: string;
    breakdownLabel: string;
    points: number;
    isFallback: boolean;
  } | null; // null = pas de pronostic IA pour ce match (idem)
}

/**
 * Carte d'un match terminé, enrichie du duel joueur/IA : score réel bien visible, ton
 * pronostic et ses points détaillés à côté, le pronostic de l'IA pour comparaison directe,
 * et qui gagne la manche. Si l'utilisateur n'a pas pronostiqué, le dit explicitement
 * plutôt que de laisser une carte ambiguë.
 */
export function FinishedMatchDuelCard({
  metaLabel,
  homeTeam,
  awayTeam,
  homePlaceholder,
  awayPlaceholder,
  homeScore,
  awayScore,
  duelStatus,
  user,
  ai,
}: FinishedMatchDuelCardProps) {
  const duelDecided = user !== null && ai !== null;
  const userWins = duelDecided && user!.points > ai!.points;
  const aiWins = duelDecided && ai!.points > user!.points;

  return (
    <div className="rounded-[22px] border border-accent/[0.28] bg-gradient-to-b from-[#1B2438] to-[#141B2C] p-[18px] shadow-[0_10px_28px_rgba(0,0,0,0.35)]">
      <div className="mb-4 flex items-center justify-between">
        <span className="num text-xs font-semibold text-ink-secondary">{metaLabel}</span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-br from-accent-light to-accent-dark px-[11px] py-1.5 text-[11px] font-bold text-[#2A1B03]">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          Pointé
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="flex flex-col items-center gap-[9px]">
          <TeamBadge team={homeTeam} />
          <span className="text-center text-[13px] font-bold text-ink">{homeTeam?.name ?? homePlaceholder ?? "?"}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-muted">Score réel</span>
          <div className="num text-2xl font-extrabold text-ink">
            {homeScore} – {awayScore}
          </div>
        </div>
        <div className="flex flex-col items-center gap-[9px]">
          <TeamBadge team={awayTeam} />
          <span className="text-center text-[13px] font-bold text-ink">{awayTeam?.name ?? awayPlaceholder ?? "?"}</span>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2 border-t border-white/[0.08] pt-3.5">
        {duelStatus === "loading" ? (
          <div className="py-2 text-center text-xs text-ink-secondary">Chargement du duel…</div>
        ) : duelStatus === "error" ? (
          <div className="py-2 text-center text-xs text-danger">Impossible de charger le duel. Réessaie plus tard.</div>
        ) : (
          <>
            {user ? (
              <DuelRow label="Toi" scoreLabel={user.scoreLabel} breakdownLabel={user.breakdownLabel} points={user.points} isWinner={userWins} />
            ) : (
              <DuelRow label="Toi" scoreLabel="" breakdownLabel="Tu n'as pas pronostiqué ce match (0 pt)" points={null} isWinner={false} />
            )}

            {ai ? (
              <DuelRow
                label="IA"
                scoreLabel={ai.scoreLabel}
                breakdownLabel={ai.breakdownLabel}
                points={ai.points}
                isWinner={aiWins}
                badge={ai.isFallback ? "repli" : undefined}
              />
            ) : (
              <DuelRow label="IA" scoreLabel="" breakdownLabel="Prono IA indisponible pour ce match" points={null} isWinner={false} />
            )}

            {duelDecided ? (
              <div className="text-center text-[11px] font-semibold text-ink-secondary">
                {userWins ? "Tu gagnes la manche" : aiWins ? "L'IA gagne la manche" : "Égalité sur ce match"}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
