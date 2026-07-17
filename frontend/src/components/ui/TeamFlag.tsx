interface TeamFlagProps {
  gradient: string;
  label: string;
  size?: number;
  favorite?: boolean;
  bold?: boolean;
}

export function TeamFlag({ gradient, label, size = 60, favorite = false, bold = false }: TeamFlagProps) {
  const labelClass = bold
    ? "text-[15px] font-bold text-ink"
    : favorite
      ? "text-xs font-semibold text-accent"
      : "text-xs font-semibold text-ink-secondary";

  return (
    <div className="flex flex-col items-center gap-[9px]">
      <div
        className="rounded-full"
        style={{
          width: size,
          height: size,
          background: gradient,
          boxShadow: favorite
            ? "0 0 0 2px rgba(242,176,61,0.9), 0 6px 14px rgba(0,0,0,0.4)"
            : "0 0 0 2px rgba(255,255,255,0.12), 0 6px 14px rgba(0,0,0,0.4)",
        }}
      />
      <span className={labelClass}>
        {label}
        {favorite ? " ★" : ""}
      </span>
    </div>
  );
}
