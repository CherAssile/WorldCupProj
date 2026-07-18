import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BrandPanel, LoginForm, RegisterForm } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useLogin } from "../hooks/useLogin";
import { useRegister } from "../hooks/useRegister";

type Mode = "login" | "register";

interface LocationState {
  from?: { pathname?: string };
}

export function Connexion() {
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAuth();
  const login = useLogin();
  const register = useRegister();
  const [mode, setMode] = useState<Mode>("login");

  const redirectTo = (location.state as LocationState | null)?.from?.pathname ?? "/accueil";

  function handleLogin(email: string, password: string) {
    login.mutate(
      { email, password },
      {
        onSuccess: (token) => {
          auth.login(token.access_token);
          navigate(redirectTo, { replace: true });
        },
      }
    );
  }

  function handleRegister(email: string, username: string, password: string) {
    register.mutate(
      { email, username, password },
      {
        onSuccess: () => handleLogin(email, password),
      }
    );
  }

  const isSubmitting = mode === "login" ? login.isPending : register.isPending || login.isPending;
  const error =
    mode === "login"
      ? login.isError
        ? login.error.message
        : null
      : register.isError
        ? register.error.message
        : login.isError
          ? login.error.message
          : null;

  const form =
    mode === "login" ? (
      <LoginForm onSubmit={handleLogin} isSubmitting={isSubmitting} error={error} />
    ) : (
      <RegisterForm onSubmit={handleRegister} isSubmitting={isSubmitting} error={error} />
    );

  const toggle =
    mode === "login" ? (
      <div className="mt-[26px] text-sm text-ink-secondary">
        Pas encore de compte ?{" "}
        <button type="button" onClick={() => setMode("register")} className="font-bold text-primary-light">
          Créer un compte
        </button>
      </div>
    ) : (
      <div className="mt-[26px] text-sm text-ink-secondary">
        Déjà un compte ?{" "}
        <button type="button" onClick={() => setMode("login")} className="font-bold text-primary-light">
          Se connecter
        </button>
      </div>
    );

  const title = mode === "login" ? "Bon retour parmi nous" : "Rejoins le Mondial";
  const subtitle =
    mode === "login" ? "Connecte-toi pour placer tes pronos." : "Crée ton compte pour commencer à pronostiquer.";

  return (
    <div className="flex min-h-screen items-center justify-center bg-app p-5 md:p-10">
      {/* Mobile */}
      <div
        className="flex w-full max-w-[440px] flex-col items-center px-3 pb-10 pt-10 md:hidden"
        style={{ backgroundImage: "radial-gradient(120% 60% at 50% 0%, rgba(34,168,90,0.16), transparent 60%)" }}
      >
        <div className="flex h-[72px] w-[72px] items-center justify-center rounded-[22px] bg-[linear-gradient(155deg,#22A85A,#16824A)] shadow-[0_14px_34px_rgba(34,168,90,0.4)]">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
          </svg>
        </div>
        <div className="mt-[22px] text-xs font-semibold uppercase tracking-[0.2em] text-accent">Mundial Pronos</div>
        <h1 className="mt-2 text-center text-[26px] font-extrabold tracking-tight">{title}</h1>
        <p className="mt-2 text-center text-sm text-ink-secondary">{subtitle}</p>

        <div className="mt-[34px] w-full">{form}</div>

        {toggle}
      </div>

      {/* Desktop */}
      <div className="hidden w-full max-w-[1040px] overflow-hidden rounded-[26px] border border-white/[0.08] bg-app shadow-[0_40px_90px_rgba(0,0,0,0.6)] md:flex">
        <BrandPanel />
        <div className="flex flex-1 flex-col justify-center px-16 py-14">
          <h1 className="text-[30px] font-extrabold tracking-tight">{title}</h1>
          <p className="mt-2 text-[15px] text-ink-secondary">{subtitle}</p>

          <div className="mt-[34px]">{form}</div>

          {toggle}
        </div>
      </div>
    </div>
  );
}
