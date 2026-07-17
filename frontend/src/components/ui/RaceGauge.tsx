interface RaceGaugeEntry {
  label: string;
  value: number;
  isLeader?: boolean;
}

interface RaceGaugeProps {
  title: string;
  rankBadge: string;
  entries: RaceGaugeEntry[];
}

/** Classement en cours pour une récompense (ex. course au Soulier d'Or). */
export function RaceGauge({ title, rankBadge, entries }: RaceGaugeProps) {
  const max = Math.max(...entries.map((entry) => entry.value), 1);

  return (
    <div className="mt-3 flex-1 rounded-2xl bg-[#0F1729] p-3.5">
      <div className="mb-[11px] flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-ink-secondary">{title}</span>
        <span className="rounded-full bg-gradient-to-br from-accent-light to-accent-dark px-2 py-[3px] text-[10px] font-extrabold text-[#2A1B03]">
          {rankBadge}
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {entries.map((entry) => (
          <div key={entry.label} className="flex items-center gap-2.5">
            <span
              className={`w-[60px] flex-shrink-0 text-xs ${
                entry.isLeader ? "font-bold text-ink" : "font-semibold text-ink-secondary"
              }`}
            >
              {entry.label}
            </span>
            <div className="h-[7px] flex-1 overflow-hidden rounded bg-elevated">
              <div
                className={`h-full rounded ${
                  entry.isLeader ? "bg-gradient-to-r from-accent-light to-accent-dark" : "bg-[#3A4A6C]"
                }`}
                style={{ width: `${(entry.value / max) * 100}%` }}
              />
            </div>
            <span
              className={`num w-3.5 flex-shrink-0 text-right text-[13px] font-extrabold ${
                entry.isLeader ? "text-accent" : "text-ink-secondary"
              }`}
            >
              {entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
