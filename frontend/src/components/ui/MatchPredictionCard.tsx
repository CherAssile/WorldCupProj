import { Button } from "./Button";
import { QualifierSelector, type QualifierOption } from "./QualifierSelector";
import { ScoreInput } from "./ScoreInput";

type MatchCardStatus = "editable" | "locked";

export interface MatchTeamInfo {
  name: string;
  fifaCode: string;
  flagUrl: string | null;
}

const CONTAINER_CLASSES: Record<MatchCardStatus, string> = {
  editable:
    "border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] shadow-[0_12px_30px_rgba(0,0,0,0.35)]",
  locked: "border border-white/[0.05] bg-[#121A2D]",
};

const META_CLASSES: Record<MatchCardStatus, string> = {
  editable: "text-ink-secondary font-semibold",
  locked: "text-[#EC7167] font-bold",
};

const BADGE_CONFIG: Record<MatchCardStatus, { label: string; textClass: string; bgClass: string; icon: JSX.Element }> = {
  editable: {
    label: "Modifiable",
    textClass: "text-primary-light",
    bgClass: "bg-primary/[0.15]",
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
      </svg>
    ),
  },
  locked: {
    label: "Verrouillé",
    textClass: "text-[#EC7167]",
    bgClass: "bg-danger/[0.15]",
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
};

function StaticScoreBox({ value }: { value: string }) {
  return (
    <div className="num flex h-[58px] w-[50px] items-center justify-center rounded-[14px] border-2 border-[#202B42] bg-[#101728] text-[28px] font-extrabold text-[#6B7488]">
      {value}
    </div>
  );
}

function TeamBadge({ team, dimmed }: { team: MatchTeamInfo; dimmed?: boolean }) {
  return team.flagUrl ? (
    <img
      src={team.flagUrl}
      alt=""
      className={`h-[46px] w-[46px] rounded-full object-cover shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${dimmed ? "grayscale-[0.4]" : ""}`}
    />
  ) : (
    <div
      className={`flex h-[46px] w-[46px] items-center justify-center rounded-full bg-elevated text-[11px] font-extrabold text-ink-secondary shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${dimmed ? "grayscale-[0.4]" : ""}`}
    >
      {team.fifaCode}
    </div>
  );
}

function TeamBlock({
  team,
  placeholder,
  dimmed,
}: {
  team: MatchTeamInfo | null;
  placeholder?: string | null;
  dimmed?: boolean;
}) {
  if (!team) {
    return (
      <div className="flex flex-col items-center gap-[9px]">
        <div className="flex h-[46px] w-[46px] items-center justify-center rounded-full border border-dashed border-line text-ink-muted">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2.5 2-2.5 3.5M12 17h.01" />
          </svg>
        </div>
        <span className="text-[13px] font-semibold text-ink-muted">{placeholder ?? "?"}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-[9px]">
      <TeamBadge team={team} dimmed={dimmed} />
      <span className={`text-[13px] font-bold ${dimmed ? "text-ink-secondary" : "text-ink"}`}>{team.name}</span>
    </div>
  );
}

interface MatchPredictionCardProps {
  status: MatchCardStatus;
  metaLabel: string;
  homeTeam: MatchTeamInfo | null;
  awayTeam: MatchTeamInfo | null;
  homePlaceholder?: string | null;
  awayPlaceholder?: string | null;
  homeScore: number | string;
  awayScore: number | string;
  onHomeScoreChange?: (value: string) => void;
  onAwayScoreChange?: (value: string) => void;
  lockedNote?: string;
  qualifier?: {
    options: readonly [QualifierOption, QualifierOption];
    value: string | null;
    onChange: (id: string) => void;
  };
  onSave?: () => void;
  saveDisabled?: boolean;
  isSaving?: boolean;
  saveError?: string | null;
  justSaved?: boolean;
}

/**
 * Carte de pronostic pour un match PAS ENCORE terminé (sans home_score/away_score en
 * base) : modifiable avant le coup d'envoi, verrouillée après. Un match sans résultat
 * connu ne doit jamais afficher de score dans les cases prévues pour ça, quel que soit
 * l'état -- les cases restent à "–" une fois verrouillé (cf. lockedNote pour afficher le
 * pronostic de l'utilisateur, explicitement distinct d'un résultat). Un match terminé et
 * pointé est un composant à part (FinishedMatchDuelCard), jamais celui-ci.
 */
export function MatchPredictionCard({
  status,
  metaLabel,
  homeTeam,
  awayTeam,
  homePlaceholder,
  awayPlaceholder,
  homeScore,
  awayScore,
  onHomeScoreChange,
  onAwayScoreChange,
  lockedNote,
  qualifier,
  onSave,
  saveDisabled = false,
  isSaving = false,
  saveError,
  justSaved = false,
}: MatchPredictionCardProps) {
  const badge = BADGE_CONFIG[status];
  const teamsDimmed = status === "locked";

  return (
    <div className={`rounded-[22px] p-[18px] ${CONTAINER_CLASSES[status]}`}>
      <div className="mb-4 flex items-center justify-between">
        <span className={`num text-xs ${META_CLASSES[status]}`}>{metaLabel}</span>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-[11px] py-1.5 text-[11px] font-bold ${badge.textClass} ${badge.bgClass}`}
        >
          {badge.icon}
          {badge.label}
        </span>
      </div>

      <div className={`grid grid-cols-[1fr_auto_1fr] items-center gap-3 ${teamsDimmed ? "opacity-[0.62]" : ""}`}>
        <TeamBlock team={homeTeam} placeholder={homePlaceholder} dimmed={teamsDimmed} />

        <div className="flex items-center gap-2">
          {status === "editable" ? (
            <>
              <ScoreInput value={homeScore} onChange={onHomeScoreChange} size="sm" />
              <span className="text-base font-bold text-ink-muted">–</span>
              <ScoreInput value={awayScore} onChange={onAwayScoreChange} size="sm" />
            </>
          ) : (
            <>
              <StaticScoreBox value={String(homeScore)} />
              <span className="text-base font-bold text-ink-muted">–</span>
              <StaticScoreBox value={String(awayScore)} />
            </>
          )}
        </div>

        <TeamBlock team={awayTeam} placeholder={awayPlaceholder} dimmed={teamsDimmed} />
      </div>

      {status === "locked" && lockedNote ? (
        <div className="num mt-3 text-center text-[11px] text-ink-secondary">{lockedNote}</div>
      ) : null}

      {status === "editable" && qualifier ? <QualifierSelector {...qualifier} /> : null}

      {status === "editable" && onSave ? (
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/[0.08] pt-3.5">
          <div className="min-h-[16px] flex-1 text-xs">
            {saveError ? (
              <span className="text-danger">{saveError}</span>
            ) : justSaved ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/[0.15] px-2.5 py-1 font-bold text-primary-light">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                Enregistré
              </span>
            ) : null}
          </div>
          <Button variant="primary" size="sm" onClick={onSave} disabled={saveDisabled || isSaving}>
            {isSaving ? "Enregistrement…" : "Enregistrer"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
