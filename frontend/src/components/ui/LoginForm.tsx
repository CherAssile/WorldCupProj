import { useState } from "react";
import { Button } from "./Button";

interface LoginFormProps {
  onSubmit?: (email: string, password: string) => void;
  onForgotPassword?: () => void;
  isSubmitting?: boolean;
  error?: string | null;
}

export function LoginForm({ onSubmit, onForgotPassword, isSubmitting = false, error }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);

  return (
    <form
      className="flex w-full flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit?.(email, password);
      }}
    >
      <div>
        <label className="mb-[7px] block text-xs font-semibold text-ink-secondary">E-mail</label>
        <div className="flex items-center gap-[11px] rounded-2xl border border-line bg-[#0F1729] px-4 py-[14px]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0 text-ink-muted">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="m22 7-10 6L2 7" />
          </svg>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="min-w-0 flex-1 bg-transparent font-sans text-[15px] font-medium text-ink"
          />
        </div>
      </div>

      <div>
        <label className="mb-[7px] block text-xs font-semibold text-ink-secondary">Mot de passe</label>
        <div
          className={`flex items-center gap-[11px] rounded-2xl bg-[#0F1729] px-4 py-[14px] transition-colors ${
            passwordFocused
              ? "border-2 border-primary shadow-[0_0_0_4px_rgba(34,168,90,0.14)]"
              : "border border-line"
          }`}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`flex-shrink-0 ${passwordFocused ? "text-primary" : "text-ink-muted"}`}
          >
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <input
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onFocus={() => setPasswordFocused(true)}
            onBlur={() => setPasswordFocused(false)}
            className="num min-w-0 flex-1 bg-transparent font-sans text-[15px] font-medium tracking-[0.15em] text-ink"
          />
          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            className="flex-shrink-0 text-ink-muted"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        </div>
        <div className="mt-2 text-right">
          <button type="button" onClick={onForgotPassword} className="text-xs font-semibold text-ink-secondary">
            Mot de passe oublié ?
          </button>
        </div>
      </div>

      {error ? <p className="text-center text-xs text-danger">{error}</p> : null}

      <Button type="submit" variant="primary" size="lg" className="mt-1 w-full" disabled={isSubmitting}>
        {isSubmitting ? "Connexion…" : "Se connecter"}
      </Button>
    </form>
  );
}
