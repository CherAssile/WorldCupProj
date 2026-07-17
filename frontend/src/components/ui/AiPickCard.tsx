interface AiPickCardProps {
  homeTeamName: string;
  awayTeamName: string;
  homeScore: number;
  awayScore: number;
  className?: string;
}

export function AiPickCard({ homeTeamName, awayTeamName, homeScore, awayScore, className = "" }: AiPickCardProps) {
  return (
    <div className={`flex items-center gap-3.5 rounded-[18px] border border-white/[0.06] bg-surface p-4 ${className}`}>
      <div className="flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-[13px] border border-primary bg-[#0F1729]">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2CC169" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M12 8V4M9 4h6" />
          <circle cx="9" cy="14" r="1.2" fill="#2CC169" />
          <circle cx="15" cy="14" r="1.2" fill="#2CC169" />
          <path d="M2 13v3M22 13v3" />
        </svg>
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] font-bold uppercase tracking-[0.08em] text-accent">Prono IA du jour</div>
        <div className="num mt-[3px] text-[15px] font-bold">
          L'IA voit {homeTeamName} <span className="text-accent">{homeScore} – {awayScore}</span> {awayTeamName}
        </div>
      </div>
    </div>
  );
}
