interface PlayerAvatarProps {
  initials: string;
  size?: number;
  flagUrl?: string | null;
}

export function PlayerAvatar({ initials, size = 46, flagUrl }: PlayerAvatarProps) {
  const badgeSize = Math.round(size * 0.41);

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#3A4A6C] to-elevated text-[15px] font-extrabold text-ink-body">
        {initials}
      </div>
      {flagUrl ? (
        <img
          src={flagUrl}
          alt=""
          className="absolute -bottom-0.5 -right-0.5 rounded-full object-cover shadow-[0_0_0_2px_#0F1729]"
          style={{ width: badgeSize, height: badgeSize }}
        />
      ) : null}
    </div>
  );
}
