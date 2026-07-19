export interface QualifierOption {
  id: string;
  label: string;
  /** Absents pour une option « par côté » (équipe encore inconnue, ex. « Vainqueur du match 101 »). */
  fifaCode?: string;
  flagUrl?: string | null;
}

interface QualifierSelectorProps {
  options: readonly [QualifierOption, QualifierOption];
  value: string | null;
  onChange: (id: string) => void;
}

/** Choix du qualifié, requis en élimination directe. Par équipe (predicted_winner_team_id)
 * quand les équipes sont connues, par côté (predicted_winner_side) sinon. */
export function QualifierSelector({ options, value, onChange }: QualifierSelectorProps) {
  return (
    <div className="mt-[18px] border-t border-white/[0.08] pt-4">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-xs font-bold tracking-[0.04em] text-ink-body">
          En cas d'égalité, qui se qualifie&nbsp;?
        </span>
        <span className="rounded-full bg-accent/[0.14] px-2 py-[3px] text-[10px] font-bold uppercase tracking-[0.08em] text-accent">
          Requis
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {options.map((option) => {
          const isActive = value === option.id;
          return (
            <button
              key={option.id}
              onClick={() => onChange(option.id)}
              className={`flex items-center justify-center gap-2.5 rounded-2xl border-2 p-[13px] font-sans text-sm font-bold transition-colors ${
                isActive
                  ? "border-accent bg-accent/[0.12] text-ink shadow-[0_0_0_3px_rgba(242,176,61,0.14)]"
                  : "border-line bg-[#0F1729] text-[#C4CBD8]"
              }`}
            >
              {option.flagUrl ? (
                <img src={option.flagUrl} alt="" className="h-[22px] w-[22px] rounded-full object-cover" />
              ) : option.fifaCode ? (
                <span className="flex h-[22px] w-[22px] items-center justify-center rounded-full bg-elevated text-[8px] font-extrabold text-ink-secondary">
                  {option.fifaCode}
                </span>
              ) : (
                <span className="flex h-[22px] w-[22px] flex-shrink-0 items-center justify-center rounded-full border border-dashed border-line text-[10px] font-extrabold text-ink-muted">
                  ?
                </span>
              )}
              <span className="min-w-0 truncate">{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
