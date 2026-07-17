type ScoreInputSize = "md" | "lg";

interface ScoreInputProps {
  value: number | string;
  onChange?: (value: string) => void;
  active?: boolean;
  size?: ScoreInputSize;
  disabled?: boolean;
}

const SIZE_CLASSES: Record<ScoreInputSize, string> = {
  lg: "h-[84px] w-[76px] rounded-[18px] text-[40px]",
  md: "h-[68px] w-[60px] rounded-[15px] text-[34px]",
};

export function ScoreInput({ value, onChange, active = false, size = "lg", disabled }: ScoreInputProps) {
  return (
    <input
      className={`num border-2 bg-[#0F1729] text-center font-extrabold text-ink ${
        active ? "border-primary shadow-[0_0_0_4px_rgba(34,168,90,0.16)]" : "border-line"
      } ${SIZE_CLASSES[size]}`}
      value={value}
      disabled={disabled}
      inputMode="numeric"
      onChange={(event) => onChange?.(event.target.value)}
    />
  );
}
