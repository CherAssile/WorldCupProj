import { PointsPill } from "./PointsPill";
import { QualifierSelector, type QualifierOption } from "./QualifierSelector";
import { ScoreInput } from "./ScoreInput";

type MatchCardStatus = "editable" | "locked" | "graded";

interface MatchTeam {
  name: string;
  flagGradient: string;
}

const CONTAINER_CLASSES: Record<MatchCardStatus, string> = {
  editable:
    "border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] shadow-[0_12px_30px_rgba(0,0,0,0.35)]",
  locked: "border border-white/[0.05] bg-[#121A2D]",
  graded:
    "border border-accent/[0.28] bg-gradient-to-b from-[#1B2438] to-[#141B2C] shadow-[0_10px_28px_rgba(0,0,0,0.35)]",
};

const META_CLASSES: Record<MatchCardStatus, string> = {
  editable: "text-ink-secondary font-semibold",
  locked: "text-[#EC7167] font-bold",
  graded: "text-ink-secondary font-semibold",
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
  graded: {
    label: "Pointé",
    textClass: "text-[#2A1B03]",
    bgClass: "bg-gradient-to-br from-accent-light to-accent-dark",
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 6 9 17l-5-5" />
      </svg>
    ),
  },
};

interface StaticScoreBoxProps {
  value: number | string;
  variant: "locked" | "graded-exact" | "graded-neutral";
}

const STATIC_SCORE_CLASSES: Record<StaticScoreBoxProps["variant"], string> = {
  locked: "border-[#202B42] bg-[#101728] text-[#6B7488]",
  "graded-exact": "border-primary bg-[#0F1729] text-ink",
  "graded-neutral": "border-line bg-[#0F1729] text-ink",
};

function StaticScoreBox({ value, variant }: StaticScoreBoxProps) {
  return (
    <div
      className={`num flex h-[58px] w-[50px] items-center justify-center rounded-[14px] border-2 text-[28px] font-extrabold ${STATIC_SCORE_CLASSES[variant]}`}
    >
      {value}
    </div>
  );
}

interface MatchPredictionCardProps {
  status: MatchCardStatus;
  metaLabel: string;
  homeTeam: MatchTeam;
  awayTeam: MatchTeam;
  homeScore: number | string;
  awayScore: number | string;
  onHomeScoreChange?: (value: string) => void;
  onAwayScoreChange?: (value: string) => void;
  isExactScore?: boolean;
  lockedNote?: string;
  resultLabel?: string;
  pointsVariant?: "exact" | "correct" | "none";
  pointsLabel?: string;
  qualifier?: {
    options: readonly [QualifierOption, QualifierOption];
    value: string | null;
    onChange: (id: string) => void;
  };
}

export function MatchPredictionCard({
  status,
  metaLabel,
  homeTeam,
  awayTeam,
  homeScore,
  awayScore,
  onHomeScoreChange,
  onAwayScoreChange,
  isExactScore = false,
  lockedNote,
  resultLabel,
  pointsVariant,
  pointsLabel,
  qualifier,
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
        <div className="flex flex-col items-center gap-[9px]">
          <div
            className={`h-[46px] w-[46px] rounded-full shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${teamsDimmed ? "grayscale-[0.4]" : ""}`}
            style={{ background: homeTeam.flagGradient }}
          />
          <span className={`text-[13px] font-bold ${teamsDimmed ? "text-ink-secondary" : "text-ink"}`}>
            {homeTeam.name}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {status === "editable" ? (
            <>
              <ScoreInput value={homeScore} onChange={onHomeScoreChange} size="sm" />
              <span className="text-base font-bold text-ink-muted">–</span>
              <ScoreInput value={awayScore} onChange={onAwayScoreChange} size="sm" />
            </>
          ) : (
            <>
              <StaticScoreBox value={homeScore} variant={status === "locked" ? "locked" : isExactScore ? "graded-exact" : "graded-neutral"} />
              <span className="text-base font-bold text-ink-muted">–</span>
              <StaticScoreBox value={awayScore} variant={status === "locked" ? "locked" : isExactScore ? "graded-exact" : "graded-neutral"} />
            </>
          )}
        </div>

        <div className="flex flex-col items-center gap-[9px]">
          <div
            className={`h-[46px] w-[46px] rounded-full shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${teamsDimmed ? "grayscale-[0.4]" : ""}`}
            style={{ background: awayTeam.flagGradient }}
          />
          <span className={`text-[13px] font-bold ${teamsDimmed ? "text-ink-secondary" : "text-ink"}`}>
            {awayTeam.name}
          </span>
        </div>
      </div>

      {status === "locked" && lockedNote ? (
        <div className="num mt-3 text-center text-[11px] text-ink-secondary">{lockedNote}</div>
      ) : null}

      {status === "graded" && resultLabel && pointsVariant && pointsLabel ? (
        <div className="mt-4 flex items-center justify-between border-t border-white/[0.08] pt-3.5">
          <span className="num text-xs text-ink-secondary">{resultLabel}</span>
          <PointsPill variant={pointsVariant} label={pointsLabel} />
        </div>
      ) : null}

      {qualifier ? <QualifierSelector {...qualifier} /> : null}
    </div>
  );
}
