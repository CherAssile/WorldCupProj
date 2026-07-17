import { useState } from "react";
import { Badge, Button, MatchCard, PointsPill, TeamFlag } from "./components/ui";

const FLAG_FRANCE = "linear-gradient(90deg,#0055A4 33%,#fff 33% 66%,#EF4135 66%)";
const FLAG_ARGENTINA = "linear-gradient(180deg,#75AADB 33%,#fff 33% 66%,#75AADB 66%)";
const FLAG_BRAZIL = "radial-gradient(circle,#2E2A8C 0 20%,#FFDF00 20% 42%,#009C3B 42%)";
const FLAG_PORTUGAL = "linear-gradient(90deg,#046A38 42%,#DA291C 42%)";

function App() {
  const [homeScore, setHomeScore] = useState("2");
  const [awayScore, setAwayScore] = useState("1");

  return (
    <main className="mx-auto max-w-[1180px] px-10 py-16">
      <h1 className="text-[34px] font-extrabold tracking-tight">Mundial Pronos</h1>

      <section className="mt-16">
        <h2 className="mb-6 text-xl font-bold tracking-tight">Boutons</h2>
        <div className="flex max-w-sm flex-col gap-3">
          <Button variant="primary">Valider mon prono</Button>
          <Button variant="secondary">Modifier</Button>
          <div className="flex gap-3">
            <Button variant="accent" size="sm" className="flex-1">
              Doubler les points
            </Button>
            <Button variant="locked" size="sm">
              Verrouillé
            </Button>
          </div>
        </div>
      </section>

      <section className="mt-16">
        <h2 className="mb-6 text-xl font-bold tracking-tight">Badges de statut</h2>
        <div className="flex flex-wrap gap-2.5">
          <Badge status="validated" />
          <Badge status="locked" />
          <Badge status="live" />
          <Badge status="upcoming" />
        </div>

        <h3 className="mb-4 mt-6 text-xs font-semibold uppercase tracking-[0.14em] text-ink-secondary">
          Pastille de points
        </h3>
        <div className="flex items-center gap-3.5">
          <PointsPill variant="exact" label="+3 pts" />
          <PointsPill variant="correct" label="+1 pt" />
          <PointsPill variant="none" label="0 pt" />
        </div>
      </section>

      <section className="mt-16">
        <h2 className="mb-6 text-xl font-bold tracking-tight">Drapeaux ronds</h2>
        <div className="flex items-start gap-5">
          <TeamFlag gradient={FLAG_FRANCE} label="FRA" />
          <TeamFlag gradient={FLAG_BRAZIL} label="BRA" />
          <TeamFlag gradient={FLAG_ARGENTINA} label="ARG" />
          <TeamFlag gradient={FLAG_PORTUGAL} label="POR" favorite />
        </div>
      </section>

      <section className="mt-16">
        <h2 className="mb-6 text-xl font-bold tracking-tight">Carte de match</h2>
        <MatchCard
          groupLabel="Groupe C · Journée 2"
          kickoffLabel="Ouvre à 21:00"
          homeTeam={{ name: "France", flagGradient: FLAG_FRANCE }}
          awayTeam={{ name: "Argentine", flagGradient: FLAG_ARGENTINA }}
          homeScore={homeScore}
          awayScore={awayScore}
          onHomeScoreChange={setHomeScore}
          onAwayScoreChange={setAwayScore}
        />
      </section>
    </main>
  );
}

export default App;
