type BadgeStatus = "validated" | "locked" | "live" | "upcoming";

interface StatusConfig {
  label: string;
  textClass: string;
  bgClass: string;
  dotClass: string;
}

const STATUS_CONFIG: Record<BadgeStatus, StatusConfig> = {
  validated: {
    label: "Validé",
    textClass: "text-success",
    bgClass: "bg-success/[0.14]",
    dotClass: "bg-success",
  },
  locked: {
    label: "Verrouillé",
    textClass: "text-[#EC7167]",
    bgClass: "bg-danger/[0.14]",
    dotClass: "bg-danger",
  },
  live: {
    label: "En jeu",
    textClass: "text-accent",
    bgClass: "bg-accent/[0.14]",
    dotClass: "bg-accent",
  },
  upcoming: {
    label: "À venir",
    textClass: "text-ink-secondary",
    bgClass: "bg-ink-secondary/[0.12]",
    dotClass: "bg-ink-secondary",
  },
};

interface BadgeProps {
  status: BadgeStatus;
  label?: string;
}

export function Badge({ status, label }: BadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-[7px] rounded-full px-[13px] py-[7px] text-xs font-bold tracking-[0.03em] ${config.textClass} ${config.bgClass}`}
    >
      <span className={`h-[7px] w-[7px] rounded-full ${config.dotClass}`} />
      {label ?? config.label}
    </span>
  );
}
