import { Badge } from "./Badge";
import { Button } from "./Button";
import { ScoreInput } from "./ScoreInput";
import { TeamFlag } from "./TeamFlag";

interface MatchCardTeam {
  name: string;
  flagGradient: string;
}

interface MatchCardProps {
  groupLabel: string;
  kickoffLabel: string;
  homeTeam: MatchCardTeam;
  awayTeam: MatchCardTeam;
  homeScore: number | string;
  awayScore: number | string;
  onHomeScoreChange?: (value: string) => void;
  onAwayScoreChange?: (value: string) => void;
  onSubmit?: () => void;
}

export function MatchCard({
  groupLabel,
  kickoffLabel,
  homeTeam,
  awayTeam,
  homeScore,
  awayScore,
  onHomeScoreChange,
  onAwayScoreChange,
  onSubmit,
}: MatchCardProps) {
  return (
    <div className="max-w-[560px] rounded-[22px] border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.45)]">
      <div className="mb-[22px] flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-secondary">{groupLabel}</span>
        <Badge status="live" label={kickoffLabel} />
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-[18px]">
        <TeamFlag gradient={homeTeam.flagGradient} label={homeTeam.name} size={58} bold />
        <div className="flex items-center gap-3">
          <ScoreInput value={homeScore} onChange={onHomeScoreChange} active size="md" />
          <span className="text-xl font-bold text-ink-muted">–</span>
          <ScoreInput value={awayScore} onChange={onAwayScoreChange} size="md" />
        </div>
        <TeamFlag gradient={awayTeam.flagGradient} label={awayTeam.name} size={58} bold />
      </div>

      <div className="my-[18px] h-px bg-white/[0.08]" />

      <div className="flex items-center justify-between gap-4">
        <span className="num text-[13px] text-ink-secondary">
          Score exact <span className="font-bold text-accent">+3 pts</span>
        </span>
        <Button variant="primary" onClick={onSubmit}>
          Valider mon prono
        </Button>
      </div>
    </div>
  );
}
