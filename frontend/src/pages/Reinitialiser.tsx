import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui";
import { useResetPassword } from "../hooks/useResetPassword";

const MIN_PASSWORD_LENGTH = 8;

function PasswordField({
  label,
  value,
  onChange,
  autoFocus = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <div>
      <label className="mb-[7px] block text-xs font-semibold text-ink-secondary">{label}</label>
      <div className="flex items-center gap-[11px] rounded-2xl border border-line bg-[#0F1729] px-4 py-[14px]">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0 text-ink-muted">
          <rect x="3" y="11" width="18" height="10" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        <input
          type="password"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="num min-w-0 flex-1 bg-transparent font-sans text-[15px] font-medium tracking-[0.15em] text-ink"
          autoFocus={autoFocus}
        />
      </div>
    </div>
  );
}

/** Nouveau mot de passe, depuis le lien e-mail (/reinitialiser?token=...). */
export function Reinitialiser() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const resetPassword = useResetPassword();

  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;
  const mismatch = confirmation.length > 0 && password !== confirmation;
  const canSubmit = password.length >= MIN_PASSWORD_LENGTH && password === confirmation;

  return (
    <div className="flex min-h-screen items-center justify-center bg-app p-5">
      <div
        className="w-full max-w-[440px] px-3 pb-10 pt-10"
        style={{ backgroundImage: "radial-gradient(120% 60% at 50% 0%, rgba(34,168,90,0.16), transparent 60%)" }}
      >
        <div className="text-center">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Mundial Pronos</div>
          <h1 className="mt-2 text-[26px] font-extrabold tracking-tight">Nouveau mot de passe</h1>
        </div>

        {token === null ? (
          <div className="mt-[34px] rounded-2xl border border-danger/[0.3] bg-danger/[0.1] px-5 py-6 text-center">
            <p className="text-sm text-danger">Lien invalide : il manque le jeton de réinitialisation.</p>
            <p className="mt-3 text-sm text-ink-secondary">
              <Link to="/mot-de-passe-oublie" className="font-bold text-primary-light">
                Demander un nouveau lien
              </Link>
            </p>
          </div>
        ) : resetPassword.isSuccess ? (
          <div className="mt-[34px] rounded-2xl border border-primary/[0.3] bg-primary/[0.08] px-5 py-6 text-center">
            <p className="text-sm text-ink-body">{resetPassword.data.message}</p>
            <div className="mt-4">
              <Link to="/connexion">
                <Button variant="primary" size="md">
                  Se connecter
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <form
            className="mt-[34px] flex w-full flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (canSubmit) resetPassword.mutate({ token, newPassword: password });
            }}
          >
            <PasswordField label="Nouveau mot de passe" value={password} onChange={setPassword} autoFocus />
            <PasswordField label="Confirme le mot de passe" value={confirmation} onChange={setConfirmation} />

            <div className="min-h-[16px] text-center text-xs">
              {tooShort ? (
                <span className="text-danger">Au moins {MIN_PASSWORD_LENGTH} caractères.</span>
              ) : mismatch ? (
                <span className="text-danger">Les deux mots de passe ne correspondent pas.</span>
              ) : resetPassword.isError ? (
                <span className="text-danger">
                  {resetPassword.error.message}{" "}
                  <Link to="/mot-de-passe-oublie" className="font-bold text-primary-light">
                    Demander un nouveau lien
                  </Link>
                </span>
              ) : null}
            </div>

            <Button type="submit" variant="primary" size="lg" className="w-full" disabled={!canSubmit || resetPassword.isPending}>
              {resetPassword.isPending ? "Enregistrement…" : "Réinitialiser le mot de passe"}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
