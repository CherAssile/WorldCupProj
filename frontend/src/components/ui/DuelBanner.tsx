interface DuelBannerProps {
  userPoints: number;
  aiPoints: number;
  matchesCompared: number;
  onClick?: () => void;
}

/** Bandeau du duel joueur/IA en mode compétitif (même esprit que le "Duel cumulé" de
 * l'entraînement) : totaux cumulés, cliquable vers le détail des manches. */
export function DuelBanner({ userPoints, aiPoints, matchesCompared, onClick }: DuelBannerProps) {
  const leading = userPoints > aiPoints ? "user" : aiPoints > userPoints ? "ai" : "tied";

  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 rounded-2xl border border-white/[0.08] bg-elevated px-4 py-3.5 text-left transition-colors hover:border-primary/[0.3]"
    >
      <div>
        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.08em] text-ink-secondary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="4" y="8" width="16" height="12" rx="2" />
            <path d="M12 8V4M9 4h6" />
            <circle cx="9" cy="14" r="1.2" fill="currentColor" />
            <circle cx="15" cy="14" r="1.2" fill="currentColor" />
          </svg>
          Duel contre l'IA
        </div>
        <div className="mt-1 text-[11px] text-ink-muted">
          {matchesCompared} match{matchesCompared !== 1 ? "s" : ""} comparé{matchesCompared !== 1 ? "s" : ""}
        </div>
      </div>
      <div className="num flex items-center gap-2 text-lg font-extrabold">
        <span className={leading === "user" ? "text-primary-light" : "text-ink"}>Toi {userPoints}</span>
        <span className="text-ink-muted">–</span>
        <span className={leading === "ai" ? "text-primary-light" : "text-ink"}>{aiPoints} IA</span>
      </div>
    </button>
  );
}
