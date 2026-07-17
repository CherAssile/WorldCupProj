import type { CSSProperties } from "react";

export interface LeaderboardPlayer {
  rank: number;
  name: string;
  initials: string;
  points: number;
  exactScores: number;
  isAI?: boolean;
}

const MEDALS: Record<number, { bg: string; text: string }> = {
  1: { bg: "#F2B03D", text: "#2A1B03" },
  2: { bg: "#C7CEDB", text: "#141A26" },
  3: { bg: "#C88A4B", text: "#241505" },
};

function ExactScoresIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#5E6982" strokeWidth="2.4">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="0.6" fill="#5E6982" />
    </svg>
  );
}

function AIAvatarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="8" width="16" height="12" rx="2" />
      <path d="M12 8V4M9 4h6" />
      <circle cx="9" cy="14" r="1.2" fill="currentColor" />
      <circle cx="15" cy="14" r="1.2" fill="currentColor" />
      <path d="M2 13v3M22 13v3" />
    </svg>
  );
}

interface LeaderboardRowProps {
  player: LeaderboardPlayer;
  highlighted?: boolean;
}

export function LeaderboardRow({ player, highlighted = false }: LeaderboardRowProps) {
  const medal = MEDALS[player.rank];

  const rowStyle: CSSProperties | undefined = highlighted
    ? undefined
    : {
        background: player.isAI ? "linear-gradient(90deg, rgba(34,168,90,0.07), #151F35 60%)" : "#151F35",
        border: medal
          ? `1px solid ${medal.bg}55`
          : player.isAI
            ? "1px solid rgba(34,168,90,0.28)"
            : "1px solid rgba(255,255,255,0.05)",
      };

  const rankStyle: CSSProperties = medal
    ? { background: medal.bg, color: medal.text, boxShadow: `0 4px 12px ${medal.bg}44` }
    : { background: "transparent", color: "#8A93A6" };

  return (
    <div
      className={`mb-2 flex items-center gap-3 rounded-2xl p-3 md:grid md:grid-cols-[64px_1fr_200px_130px] md:gap-4 md:px-5 md:py-3.5 ${
        highlighted
          ? "border border-primary bg-primary/[0.14] shadow-[0_0_0_3px_rgba(34,168,90,0.12)]"
          : ""
      }`}
      style={rowStyle}
    >
      <div
        className="num flex h-[34px] w-[34px] flex-shrink-0 items-center justify-center rounded-[10px] text-[15px] font-extrabold"
        style={rankStyle}
      >
        {player.rank}
      </div>

      <div className="flex min-w-0 flex-1 items-center gap-3 md:flex-none">
        <div
          className={`flex h-[38px] w-[38px] flex-shrink-0 items-center justify-center rounded-full text-sm font-extrabold ${
            highlighted
              ? "bg-gradient-to-br from-primary to-primary-dark text-[#06210F]"
              : player.isAI
                ? "border border-primary bg-[#0F1729] text-primary-light"
                : "bg-elevated text-ink-body"
          }`}
        >
          {player.isAI && !highlighted ? <AIAvatarIcon /> : player.initials}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-[7px]">
            <span className="truncate text-[15px] font-bold">{player.name}</span>
            {player.isAI ? (
              <span className="flex-shrink-0 rounded-md bg-primary/[0.16] px-1.5 py-0.5 text-[9px] font-extrabold tracking-[0.1em] text-primary-light">
                IA
              </span>
            ) : null}
          </div>
          <div className="num mt-[3px] flex items-center gap-[5px] text-xs text-[#8A93A6] md:hidden">
            <ExactScoresIcon />
            {player.exactScores} scores exacts
          </div>
        </div>
      </div>

      <div className="num hidden items-center justify-end gap-[7px] text-[15px] font-semibold text-ink-secondary md:flex">
        <ExactScoresIcon size={14} />
        {player.exactScores}
      </div>

      <div className="num flex-shrink-0 text-[19px] font-extrabold text-accent md:text-right md:text-[22px]">
        {player.points}
      </div>
    </div>
  );
}
