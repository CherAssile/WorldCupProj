interface OddsGaugeProps {
  label: string;
  percent: number;
  rankBadge: string;
}

/** Cote actuelle d'un joueur pronostiqué pour une récompense (ex. Ballon d'Or). */
export function OddsGauge({ label, percent, rankBadge }: OddsGaugeProps) {
  return (
    <div className="mt-3 flex flex-1 items-center gap-2.5 rounded-2xl bg-[#0F1729] p-3.5">
      <span className="flex-shrink-0 text-[11px] font-bold uppercase tracking-[0.08em] text-ink-secondary">
        {label}
      </span>
      <div className="h-[7px] flex-1 overflow-hidden rounded bg-elevated">
        <div
          className="h-full rounded bg-gradient-to-r from-accent-light to-accent-dark"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="flex-shrink-0 text-[11px] font-extrabold text-accent">{rankBadge}</span>
    </div>
  );
}
