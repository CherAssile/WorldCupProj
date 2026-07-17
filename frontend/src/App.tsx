import { Navigate, Route, Routes } from "react-router-dom";
import { Accueil } from "./pages/Accueil";
import { Classement } from "./pages/Classement";
import { Connexion } from "./pages/Connexion";
import { Pronostics } from "./pages/Pronostics";
import { Recompenses } from "./pages/Recompenses";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/accueil" replace />} />
      <Route path="/connexion" element={<Connexion />} />
      <Route path="/accueil" element={<Accueil />} />
      <Route path="/pronostics" element={<Pronostics />} />
      <Route path="/classement" element={<Classement />} />
      <Route path="/recompenses" element={<Recompenses />} />
    </Routes>
  );
}

export default App;
