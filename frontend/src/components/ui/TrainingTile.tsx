interface TrainingTileProps {
  record: string;
  onClick?: () => void;
}

export function TrainingTile({ record, onClick }: TrainingTileProps) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col justify-between rounded-[18px] border border-primary/[0.3] bg-[linear-gradient(155deg,#173A2A,#122A1F)] p-4 text-left md:rounded-[20px] md:p-5"
    >
      <div className="flex items-center gap-2 text-primary-light">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M12 8V4M9 4h6" />
          <circle cx="9" cy="14" r="1.2" fill="currentColor" />
          <circle cx="15" cy="14" r="1.2" fill="currentColor" />
        </svg>
        <span className="text-[11px] font-bold uppercase tracking-[0.06em]">Entraînement</span>
      </div>
      <div className="mt-2.5 text-sm font-bold md:mt-3 md:text-base">Défie l'IA</div>
      <div className="mt-0.5 flex items-center justify-between gap-2 text-xs text-ink-secondary md:mt-2 md:text-[13px]">
        Duel : {record}
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="flex-shrink-0 text-primary-light"
        >
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </div>
    </button>
  );
}
