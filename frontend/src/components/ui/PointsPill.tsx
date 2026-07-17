type PointsVariant = "exact" | "correct" | "none";

const VARIANT_CLASSES: Record<PointsVariant, string> = {
  exact:
    "bg-gradient-to-br from-accent-light to-accent-dark text-[#2A1B03] shadow-[0_4px_14px_rgba(224,149,42,0.35)]",
  correct: "bg-elevated text-ink-body",
  none: "bg-elevated text-ink-muted",
};

interface PointsPillProps {
  variant: PointsVariant;
  label: string;
}

export function PointsPill({ variant, label }: PointsPillProps) {
  return (
    <span
      className={`num inline-flex items-center gap-1.5 rounded-xl px-[15px] py-2 text-base font-extrabold ${VARIANT_CLASSES[variant]}`}
    >
      {label}
    </span>
  );
}
