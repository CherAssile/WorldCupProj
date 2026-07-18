import { Button } from "./Button";
import { CountdownTimer } from "./CountdownTimer";

interface NextMatchHeroTeam {
  name: string;
  fifaCode: string;
  flagUrl: string | null;
}

function TeamBadge({ team, className = "" }: { team: NextMatchHeroTeam; className?: string }) {
  return team.flagUrl ? (
    <img
      src={team.flagUrl}
      alt=""
      className={`flex-shrink-0 rounded-full object-cover shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${className}`}
    />
  ) : (
    <div
      className={`flex flex-shrink-0 items-center justify-center rounded-full bg-elevated text-xs font-extrabold text-ink-secondary shadow-[0_0_0_2px_rgba(255,255,255,0.12)] ${className}`}
    >
      {team.fifaCode}
    </div>
  );
}

interface NextMatchHeroProps {
  groupLabel: string;
  kickoffLabel: string;
  homeTeam: NextMatchHeroTeam;
  awayTeam: NextMatchHeroTeam;
  countdownTarget: Date;
  onPredict?: () => void;
}

/** Carte vedette du prochain match sur l'écran d'accueil : équipes, compte à rebours, CTA. */
export function NextMatchHero({
  groupLabel,
  kickoffLabel,
  homeTeam,
  awayTeam,
  countdownTarget,
  onPredict,
}: NextMatchHeroProps) {
  return (
    <div className="rounded-[22px] border border-primary/[0.28] bg-[linear-gradient(165deg,#1C2C4E,#121A2E)] p-5 shadow-[0_16px_36px_rgba(0,0,0,0.4)] md:bg-[linear-gradient(150deg,#1C2C4E,#121A2E)] md:p-[26px]">
      <div className="mb-[18px] flex items-center justify-between md:mb-[22px]">
        <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-primary-light md:text-xs">
          {groupLabel}
        </span>
        <span className="text-[11px] font-semibold text-ink-secondary md:text-[13px]">{kickoffLabel}</span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2.5 md:gap-6">
        <div className="flex flex-col items-center gap-2.5 md:flex-row md:justify-end md:gap-3.5">
          <TeamBadge team={homeTeam} className="order-1 h-[50px] w-[50px] md:order-2 md:h-[58px] md:w-[58px]" />
          <span className="order-2 text-[13px] font-bold md:order-1 md:text-xl">{homeTeam.name}</span>
        </div>
        <span className="text-[15px] font-extrabold text-ink-muted md:text-lg">VS</span>
        <div className="flex flex-col items-center gap-2.5 md:flex-row md:gap-3.5">
          <TeamBadge team={awayTeam} className="h-[50px] w-[50px] md:h-[58px] md:w-[58px]" />
          <span className="text-[13px] font-bold md:text-xl">{awayTeam.name}</span>
        </div>
      </div>

      <div className="mt-[18px] flex flex-col gap-3.5 md:mt-6 md:flex-row md:items-center md:gap-5">
        <CountdownTimer target={countdownTarget} />
        <Button variant="primary" size="lg" onClick={onPredict} className="w-full md:w-auto">
          <span className="md:hidden">Pronostiquer maintenant</span>
          <span className="hidden md:inline">Pronostiquer</span>
        </Button>
      </div>
    </div>
  );
}
