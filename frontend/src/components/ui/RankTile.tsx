interface RankTileProps {
  rank: number;
  totalPlayers: number;
  deltaLabel: string;
}

export function RankTile({ rank, totalPlayers, deltaLabel }: RankTileProps) {
  return (
    <div className="rounded-[18px] border border-white/[0.06] bg-surface p-4 md:rounded-[20px] md:p-5">
      <div className="mb-3 flex items-center gap-2 text-ink-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F2B03D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9H4a2 2 0 0 1 0-4h2M18 9h2a2 2 0 0 0 0-4h-2M6 5h12v4a6 6 0 0 1-12 0zM8 21h8M12 15v6" />
        </svg>
        <span className="text-[11px] font-bold uppercase tracking-[0.06em]">Ton rang</span>
      </div>
      <div className="num text-[30px] font-extrabold md:text-[34px]">
        {rank}
        <span className="text-[15px] font-bold text-ink-muted md:text-base"> / {totalPlayers}</span>
      </div>
      <div className="mt-1 text-xs font-semibold text-primary-light md:text-[13px]">▲ {deltaLabel}</div>
    </div>
  );
}
