import { useLocation, useNavigate } from "react-router-dom";
import { BottomNav } from "./ui";

type NavId = "accueil" | "matchs" | "classement" | "profil";

const ROUTES: Record<NavId, string> = {
  accueil: "/accueil",
  matchs: "/pronostics",
  classement: "/classement",
  profil: "/profil",
};

// Écrans pas encore implémentés : la nav les affiche mais ne navigue pas encore.
const IMPLEMENTED_ROUTES = new Set<string>([ROUTES.accueil, ROUTES.matchs, ROUTES.classement]);

export function AppBottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const active =
    (Object.keys(ROUTES) as NavId[]).find((id) => ROUTES[id] === location.pathname) ?? "accueil";

  return (
    <BottomNav
      active={active}
      onChange={(id) => {
        const path = ROUTES[id];
        if (IMPLEMENTED_ROUTES.has(path)) navigate(path);
      }}
    />
  );
}
