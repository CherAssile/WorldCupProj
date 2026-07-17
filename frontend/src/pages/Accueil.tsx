import { useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { AppTopNav } from "../components/AppTopNav";
import { AiPickCard, NextMatchHero, RankTile, TotalPointsBadge, TrainingTile } from "../components/ui";
import { FLAG_ARGENTINA, FLAG_FRANCE } from "../lib/flagGradients";

const LOCK_DURATION_MS = (2 * 3600 + 14 * 60 + 37) * 1000;

export function Accueil() {
  const [countdownTarget] = useState(() => new Date(Date.now() + LOCK_DURATION_MS));

  return (
    <div className="min-h-screen bg-app">
      <AppTopNav points={128} />

      <div className="mx-auto max-w-[440px] md:max-w-[1040px]">
        <header className="flex items-center justify-between px-5 pb-1 pt-4 md:hidden">
          <div>
            <div className="text-[13px] text-ink-secondary">Bonsoir,</div>
            <div className="text-2xl font-extrabold tracking-tight">Thomas</div>
          </div>
          <TotalPointsBadge points={128} />
        </header>
        <header className="hidden px-8 pb-0 pt-7 md:block">
          <div className="text-sm text-ink-secondary">Bonsoir,</div>
          <h1 className="mt-0.5 text-[30px] font-extrabold tracking-tight">Thomas</h1>
        </header>

        <div className="px-5 pb-2 pt-4 md:grid md:grid-cols-[1.7fr_1fr] md:gap-5 md:px-8 md:pb-9 md:pt-[22px]">
          <NextMatchHero
            groupLabel="Prochain match · Groupe C"
            kickoffLabel="Auj. 21:00"
            homeTeam={{ name: "France", flagGradient: FLAG_FRANCE }}
            awayTeam={{ name: "Argentine", flagGradient: FLAG_ARGENTINA }}
            countdownTarget={countdownTarget}
          />

          <div className="mt-3.5 grid grid-cols-2 gap-3 md:mt-0 md:flex md:flex-col md:gap-4">
            <RankTile rank={27} totalPlayers={41} deltaLabel="3 places" />
            <TrainingTile record="3–2 pour toi" />
            <AiPickCard
              homeTeamName="France"
              awayTeamName="Argentine"
              homeScore={2}
              awayScore={1}
              className="col-span-2 hidden md:flex"
            />
          </div>
        </div>

        <div className="px-5 pb-8 md:hidden">
          <AiPickCard homeTeamName="France" awayTeamName="Argentine" homeScore={2} awayScore={1} />
        </div>
      </div>

      <div className="md:hidden">
        <AppBottomNav />
      </div>
    </div>
  );
}
