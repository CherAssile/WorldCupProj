import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "accent" | "locked";
type ButtonSize = "lg" | "md" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-primary text-[#06210F] shadow-[0_6px_18px_rgba(34,168,90,0.32)] hover:bg-primary-light",
  secondary: "border border-line bg-transparent text-ink-body hover:border-ink-secondary",
  accent: "bg-accent text-[#2A1B03] hover:bg-accent-light",
  locked: "cursor-not-allowed border border-line bg-transparent text-ink-muted opacity-55",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  lg: "rounded-2xl px-[22px] py-4 text-base",
  md: "rounded-2xl px-[22px] py-[15px] text-[15px]",
  sm: "rounded-2xl px-[18px] py-[13px] text-sm",
};

export function Button({ variant = "primary", size = "md", className = "", disabled, ...props }: ButtonProps) {
  return (
    <button
      disabled={disabled || variant === "locked"}
      className={`font-sans font-bold transition-colors ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...props}
    />
  );
}
