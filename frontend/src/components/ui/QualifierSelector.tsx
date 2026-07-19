export interface QualifierOption {
  id: string;
  label: string;
  /** Libellé court pour les petites largeurs (mobile). Ex. « FRA/ESP » vs « France ou Espagne ». */
  labelShort?: string;
  /** Absents pour une option « par côté » (équipe encore inconnue, ex. « France ou Espagne »). */
  fifaCode?: string;
  flagUrl?: string | null;
}

interface QualifierSelectorProps {
  options: readonly [QualifierOption, QualifierOption];
  value: string | null;
  onChange: (id: string) => void;
}

function OptionBadge({ option }: { option: QualifierOption }) {
  if (option.flagUrl) {
    return <img src={option.flagUrl} alt="" className="h-6 w-6 flex-shrink-0 rounded-full object-cover" />;
  }
  if (option.fifaCode) {
    return (
      <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-elevated text-[9px] font-extrabold text-ink-secondary">
        {option.fifaCode}
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-dashed border-line text-[11px] font-extrabold text-ink-muted">
      ?
    </span>
  );
}

/** Choix du qualifié, requis en élimination directe. Par équipe (predicted_winner_team_id)
 * quand les équipes sont connues, par côté (predicted_winner_side) sinon. Chaque option
 * s'affiche sur deux lignes (jamais tronquée) : libellé court sur mobile, complet dès sm. */
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
          const hasShort = option.labelShort != null && option.labelShort !== option.label;
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => onChange(option.id)}
              aria-pressed={isActive}
              className={`relative flex min-h-[72px] flex-col items-center justify-center gap-1.5 rounded-2xl border-2 px-2.5 py-3 text-center font-sans transition-colors ${
                isActive
                  ? "border-accent bg-accent/[0.14] text-ink shadow-[0_0_0_3px_rgba(242,176,61,0.2)]"
                  : "border-line bg-[#0F1729] text-[#C4CBD8]"
              }`}
            >
              {isActive ? (
                <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-accent">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#2A1B03" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                </span>
              ) : null}
              <OptionBadge option={option} />
              <span className="line-clamp-2 text-[13px] font-bold leading-tight [overflow-wrap:anywhere]">
                {hasShort ? (
                  <>
                    <span className="sm:hidden">{option.labelShort}</span>
                    <span className="hidden sm:inline">{option.label}</span>
                  </>
                ) : (
                  option.label
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
