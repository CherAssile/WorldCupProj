import { useLocation, useNavigate } from "react-router-dom";
import { BottomNav } from "./ui";

type NavId = "matchs" | "classement" | "ligues" | "profil";

const ROUTES: Record<NavId, string> = {
  matchs: "/pronostics",
  classement: "/classement",
  ligues: "/ligues",
  profil: "/profil",
};

// Écrans pas encore implémentés : la nav les affiche mais ne navigue pas encore.
const IMPLEMENTED_ROUTES = new Set<string>([ROUTES.matchs, ROUTES.classement]);

export function AppBottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const active =
    (Object.keys(ROUTES) as NavId[]).find((id) => ROUTES[id] === location.pathname) ?? "matchs";

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
