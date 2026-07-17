import { Navigate, Route, Routes } from "react-router-dom";
import { Classement } from "./pages/Classement";
import { Pronostics } from "./pages/Pronostics";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/pronostics" replace />} />
      <Route path="/pronostics" element={<Pronostics />} />
      <Route path="/classement" element={<Classement />} />
    </Routes>
  );
}

export default App;
