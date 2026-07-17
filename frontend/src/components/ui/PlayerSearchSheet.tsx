import { useState } from "react";
import { PlayerAvatar } from "./PlayerAvatar";

export interface AwardPlayerOption {
  id: string;
  name: string;
  initials: string;
  position: string;
  shirtNumber: number;
  teamName: string;
  teamFlagGradient: string;
}

interface PlayerGroup {
  teamName: string;
  teamFlagGradient: string;
  players: AwardPlayerOption[];
}

function groupByTeam(players: AwardPlayerOption[]): PlayerGroup[] {
  const groups: PlayerGroup[] = [];
  for (const player of players) {
    const group = groups.find((g) => g.teamName === player.teamName);
    if (group) {
      group.players.push(player);
    } else {
      groups.push({ teamName: player.teamName, teamFlagGradient: player.teamFlagGradient, players: [player] });
    }
  }
  return groups;
}

interface PlayerSearchSheetProps {
  categoryLabel: string;
  players: AwardPlayerOption[];
  totalPlayerCount: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onConfirm: () => void;
  onClose: () => void;
}

/** Sélecteur de joueur pour une récompense : bottom sheet sur mobile, dialog centré sur desktop. */
export function PlayerSearchSheet({
  categoryLabel,
  players,
  totalPlayerCount,
  selectedId,
  onSelect,
  onConfirm,
  onClose,
}: PlayerSearchSheetProps) {
  const [query, setQuery] = useState("");

  const filtered = players.filter((player) => player.name.toLowerCase().includes(query.toLowerCase()));
  const groups = groupByTeam(filtered);
  const selectedPlayer = players.find((player) => player.id === selectedId);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/55 backdrop-blur-[2px] md:items-center md:bg-black/60 md:backdrop-blur-none">
      <div className="flex max-h-[85vh] w-full flex-col rounded-t-[28px] border-t border-white/10 bg-[#0F1729] md:max-h-[560px] md:w-[560px] md:rounded-[22px] md:border">
        <div className="flex justify-center pt-2.5 md:hidden">
          <div className="h-1 w-10 rounded-full bg-[#2E3C57]" />
        </div>

        <div className="flex items-center justify-between px-5 pb-1.5 pt-3 md:px-6 md:pb-3.5 md:pt-[22px]">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">{categoryLabel}</div>
            <div className="text-lg font-extrabold md:text-xl">Choisir un joueur</div>
          </div>
          <button
            onClick={onClose}
            className="flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-[11px] bg-elevated text-ink-secondary md:h-9 md:w-9"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div className="px-5 pb-3 pt-2 md:px-6 md:pb-3.5">
          <div className="flex items-center gap-2.5 rounded-2xl border-2 border-primary bg-app px-[15px] py-[13px] shadow-[0_0_0_4px_rgba(34,168,90,0.14)] md:py-3.5">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              className="flex-shrink-0 text-primary"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4-4" />
            </svg>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={`Rechercher parmi ${totalPlayerCount.toLocaleString("fr-FR")} joueurs…`}
              className="min-w-0 flex-1 bg-transparent font-sans text-[15px] font-semibold text-ink placeholder:text-ink-muted"
            />
            {query ? (
              <button
                onClick={() => setQuery("")}
                className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[#2E3C57] text-ink-secondary"
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-3 md:px-4">
          {groups.map((group) => (
            <div key={group.teamName}>
              <div className="flex items-center gap-2.5 px-2.5 py-2">
                <div className="h-5 w-5 flex-shrink-0 rounded-full" style={{ background: group.teamFlagGradient }} />
                <span className="text-xs font-bold uppercase tracking-[0.06em] text-ink-secondary">
                  {group.teamName}
                </span>
                <span className="text-[11px] text-ink-muted">· {group.players.length} joueurs</span>
              </div>
              {group.players.map((player) => {
                const isSelected = player.id === selectedId;
                return (
                  <button
                    key={player.id}
                    onClick={() => onSelect(player.id)}
                    className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left ${
                      isSelected ? "border border-primary bg-primary/[0.13]" : ""
                    }`}
                  >
                    <PlayerAvatar initials={player.initials} size={38} />
                    <div className="min-w-0 flex-1">
                      <div className="text-[15px] font-bold">{player.name}</div>
                      <div className="text-xs text-ink-secondary">
                        {player.position} · nº {player.shirtNumber}
                      </div>
                    </div>
                    {isSelected ? (
                      <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#06210F" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      </div>
                    ) : (
                      <div className="h-[22px] w-[22px] flex-shrink-0 rounded-full border-2 border-[#2E3C57]" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="border-t border-white/[0.08] px-5 pb-[22px] pt-3 md:hidden">
          <button
            disabled={!selectedPlayer}
            onClick={onConfirm}
            className="h-[52px] w-full rounded-2xl bg-primary font-sans text-base font-bold text-[#06210F] shadow-[0_8px_22px_rgba(34,168,90,0.32)] disabled:opacity-50"
          >
            Confirmer{selectedPlayer ? ` · ${selectedPlayer.name}` : ""}
          </button>
        </div>

        <div className="hidden gap-3 border-t border-white/[0.08] px-6 pb-[22px] pt-4 md:flex">
          <button
            onClick={onClose}
            className="h-[52px] flex-shrink-0 rounded-[15px] border border-line px-6 font-sans text-[15px] font-semibold text-ink-body"
          >
            Annuler
          </button>
          <button
            disabled={!selectedPlayer}
            onClick={onConfirm}
            className="h-[52px] flex-1 rounded-[15px] bg-primary font-sans text-base font-bold text-[#06210F] shadow-[0_8px_22px_rgba(34,168,90,0.32)] disabled:opacity-50"
          >
            Confirmer{selectedPlayer ? ` · ${selectedPlayer.name}` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}
