import type { ReactNode } from "react";
import { PlayerAvatar } from "./PlayerAvatar";

interface AwardCardSelectedPlayer {
  name: string;
  initials: string;
  position: string;
  teamName: string;
  teamFlagGradient: string;
}

interface AwardCardProps {
  icon: JSX.Element;
  title: string;
  subtitle: string;
  deadlineDate: string;
  selectedPlayer?: AwardCardSelectedPlayer;
  onOpenSelector: () => void;
  children?: ReactNode;
}

/** Carte d'une catégorie de récompense : choisie (joueur + jauge) ou vide (à choisir). */
export function AwardCard({
  icon,
  title,
  subtitle,
  deadlineDate,
  selectedPlayer,
  onOpenSelector,
  children,
}: AwardCardProps) {
  return (
    <div
      className={`flex flex-col rounded-[20px] p-4 md:p-5 ${
        selectedPlayer
          ? "border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33]"
          : "border border-dashed border-[#2E3C57] bg-[#121A2D]"
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-[13px] ${
            selectedPlayer ? "bg-accent/[0.14] text-accent" : "bg-ink-secondary/[0.1] text-ink-secondary"
          }`}
        >
          {icon}
        </div>
        <div>
          <div className="text-base font-bold md:text-[17px]">{title}</div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-secondary">{subtitle}</div>
        </div>
      </div>

      {selectedPlayer ? (
        <>
          <button
            onClick={onOpenSelector}
            className="mt-3.5 flex items-center gap-3 rounded-2xl bg-[#0F1729] p-3 text-left"
          >
            <PlayerAvatar
              initials={selectedPlayer.initials}
              size={46}
              teamFlagGradient={selectedPlayer.teamFlagGradient}
            />
            <div className="min-w-0 flex-1">
              <div className="text-base font-bold">{selectedPlayer.name}</div>
              <div className="text-xs text-ink-secondary">
                {selectedPlayer.teamName} · {selectedPlayer.position}
              </div>
            </div>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#5E6982"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="flex-shrink-0"
            >
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>

          {children}

          <div className="mt-3 flex items-center justify-end gap-1.5 text-[11px] text-[#8A93A6]">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8A93A6" strokeWidth="2.2" strokeLinecap="round">
              <rect x="3" y="11" width="18" height="10" rx="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            Modifiable jusqu'au {deadlineDate} · 21:00
          </div>
        </>
      ) : (
        <>
          <button
            onClick={onOpenSelector}
            className="mt-3.5 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-[#3A4A66] py-[15px] font-sans text-sm font-bold text-ink-body md:hidden"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#22A85A" strokeWidth="2.4" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Choisir un joueur
          </button>
          <div className="mt-3 flex items-center justify-center gap-1.5 text-[11px] text-accent-dark md:hidden">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M12 8v4M12 16h.01" />
              <circle cx="12" cy="12" r="9" />
            </svg>
            Aucun choix — à faire avant le {deadlineDate}
          </div>

          <div className="hidden flex-1 flex-col items-center justify-center gap-3.5 py-6 md:flex">
            <div className="flex h-[52px] w-[52px] items-center justify-center rounded-full bg-elevated text-ink-muted">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <div className="text-center">
              <div className="text-sm font-bold text-ink-body">Pas encore de choix</div>
              <div className="mt-1 text-xs text-accent-dark">À faire avant le {deadlineDate}</div>
            </div>
            <button
              onClick={onOpenSelector}
              className="inline-flex h-[52px] items-center gap-2 rounded-2xl bg-primary px-6 font-sans text-sm font-bold text-[#06210F]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Choisir un joueur
            </button>
          </div>
        </>
      )}
    </div>
  );
}
