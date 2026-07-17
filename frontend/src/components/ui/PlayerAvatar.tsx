interface PlayerAvatarProps {
  initials: string;
  size?: number;
  teamFlagGradient?: string;
}

export function PlayerAvatar({ initials, size = 46, teamFlagGradient }: PlayerAvatarProps) {
  const badgeSize = Math.round(size * 0.41);

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#3A4A6C] to-elevated text-[15px] font-extrabold text-ink-body">
        {initials}
      </div>
      {teamFlagGradient ? (
        <div
          className="absolute -bottom-0.5 -right-0.5 rounded-full shadow-[0_0_0_2px_#0F1729]"
          style={{ width: badgeSize, height: badgeSize, background: teamFlagGradient }}
        />
      ) : null}
    </div>
  );
}
