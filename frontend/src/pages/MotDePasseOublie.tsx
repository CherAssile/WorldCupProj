import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui";
import { useForgotPassword } from "../hooks/useForgotPassword";

/** Demande de réinitialisation : un champ e-mail, une confirmation neutre (anti-énumération). */
export function MotDePasseOublie() {
  const [email, setEmail] = useState("");
  const forgotPassword = useForgotPassword();

  return (
    <div className="flex min-h-screen items-center justify-center bg-app p-5">
      <div
        className="w-full max-w-[440px] px-3 pb-10 pt-10"
        style={{ backgroundImage: "radial-gradient(120% 60% at 50% 0%, rgba(34,168,90,0.16), transparent 60%)" }}
      >
        <div className="text-center">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Mundial Pronos</div>
          <h1 className="mt-2 text-[26px] font-extrabold tracking-tight">Mot de passe oublié</h1>
          <p className="mt-2 text-sm text-ink-secondary">
            Indique ton e-mail : si un compte existe, tu recevras un lien de réinitialisation valable 1 heure.
          </p>
        </div>

        {forgotPassword.isSuccess ? (
          <div className="mt-[34px] rounded-2xl border border-primary/[0.3] bg-primary/[0.08] px-5 py-6 text-center">
            <p className="text-sm text-ink-body">{forgotPassword.data.message}</p>
            <p className="mt-2 text-xs text-ink-secondary">
              Pense à vérifier tes courriers indésirables. Le lien expire dans une heure.
            </p>
          </div>
        ) : (
          <form
            className="mt-[34px] flex w-full flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (email.trim()) forgotPassword.mutate(email.trim());
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
                  autoFocus
                />
              </div>
            </div>

            {forgotPassword.isError ? (
              <p className="text-center text-xs text-danger">{forgotPassword.error.message}</p>
            ) : null}

            <Button type="submit" variant="primary" size="lg" className="mt-1 w-full" disabled={forgotPassword.isPending}>
              {forgotPassword.isPending ? "Envoi…" : "Envoyer le lien"}
            </Button>
          </form>
        )}

        <div className="mt-[26px] text-center text-sm text-ink-secondary">
          <Link to="/connexion" className="font-bold text-primary-light">
            Retour à la connexion
          </Link>
        </div>
      </div>
    </div>
  );
}
