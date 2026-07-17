import { Link, useLocation } from "react-router-dom";
import { TotalPointsBadge } from "./ui";

const NAV_LINKS = [
  { label: "Accueil", path: "/accueil" },
  { label: "Matchs", path: "/pronostics" },
  { label: "Classement", path: "/classement" },
  { label: "Récompenses", path: "/recompenses" },
];

interface AppTopNavProps {
  points: number;
  userInitials?: string;
}

/** Barre de navigation desktop partagée (masquée sur mobile, où AppBottomNav prend le relais). */
export function AppTopNav({ points, userInitials = "TB" }: AppTopNavProps) {
  const location = useLocation();

  return (
    <div className="hidden items-center justify-between border-b border-white/[0.08] px-8 py-5 md:flex">
      <Link to="/accueil" className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[linear-gradient(155deg,#22A85A,#16824A)]">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
          </svg>
        </div>
        <span className="text-[17px] font-extrabold tracking-tight">Mundial Pronos</span>
      </Link>

      <div className="flex items-center gap-[26px]">
        {NAV_LINKS.map((link) => (
          <Link
            key={link.path}
            to={link.path}
            className={`text-sm ${
              location.pathname === link.path ? "font-bold text-ink" : "font-medium text-ink-secondary"
            }`}
          >
            {link.label}
          </Link>
        ))}
        <TotalPointsBadge points={points} />
        <div className="flex h-[38px] w-[38px] items-center justify-center rounded-full bg-[linear-gradient(135deg,#22A85A,#16824A)] text-sm font-extrabold text-[#06210F]">
          {userInitials}
        </div>
      </div>
    </div>
  );
}
