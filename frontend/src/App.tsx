import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Accueil } from "./pages/Accueil";
import { Bracket } from "./pages/Bracket";
import { Classement } from "./pages/Classement";
import { Connexion } from "./pages/Connexion";
import { Entrainement } from "./pages/Entrainement";
import { Pronostics } from "./pages/Pronostics";
import { Recompenses } from "./pages/Recompenses";

function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Connexion />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/accueil" replace />} />
        <Route path="/accueil" element={<Accueil />} />
        <Route path="/pronostics" element={<Pronostics />} />
        <Route path="/classement" element={<Classement />} />
        <Route path="/recompenses" element={<Recompenses />} />
        <Route path="/bracket" element={<Bracket />} />
        <Route path="/entrainement" element={<Entrainement />} />
      </Route>
    </Routes>
  );
}

export default App;
