import { useState } from "react";
import {
  BottomNav,
  MatchPredictionCard,
  PhaseTabs,
  TotalPointsBadge,
  type Phase,
} from "../components/ui";
import {
  FLAG_ARGENTINA,
  FLAG_BRAZIL,
  FLAG_CROATIA,
  FLAG_FRANCE,
  FLAG_GERMANY,
  FLAG_NETHERLANDS,
  FLAG_PORTUGAL,
  FLAG_SPAIN,
} from "../lib/flagGradients";

const KNOCKOUT_TITLES: Record<Exclude<Phase, "groupes">, string> = {
  huitiemes: "8es de finale",
  quarts: "Quarts de finale",
  demies: "Demi-finales",
  finale: "Finale",
};

export function Pronostics() {
  const [phase, setPhase] = useState<Phase>("groupes");
  const [card1Home, setCard1Home] = useState("");
  const [card1Away, setCard1Away] = useState("");
  const [koHome, setKoHome] = useState("1");
  const [koAway, setKoAway] = useState("1");
  const [qualifier, setQualifier] = useState<string | null>(null);

  const isGroupes = phase === "groupes";

  return (
    <div className="mx-auto flex min-h-screen max-w-[440px] flex-col bg-app">
      <header className="flex items-start justify-between px-5 pb-1 pt-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Coupe du monde 2026</div>
          <h1 className="mt-[3px] text-[30px] font-extrabold tracking-tight">Pronostics</h1>
        </div>
        <TotalPointsBadge points={128} />
      </header>

      <div className="px-5 pb-4 pt-[18px]">
        <PhaseTabs value={phase} onChange={setPhase} />
      </div>

      <main className="flex-1 px-5 pb-6">
        {isGroupes ? (
          <div>
            <div className="flex items-center justify-between px-0.5 pb-3.5 pt-1.5">
              <span className="text-[15px] font-bold">Journée 2</span>
              <span className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-secondary">
                Groupe C · 5 déc.
              </span>
            </div>

            <div className="flex flex-col gap-3.5">
              <MatchPredictionCard
                status="editable"
                metaLabel="Coup d'envoi · 21:00"
                homeTeam={{ name: "France", flagGradient: FLAG_FRANCE }}
                awayTeam={{ name: "Argentine", flagGradient: FLAG_ARGENTINA }}
                homeScore={card1Home}
                awayScore={card1Away}
                onHomeScoreChange={setCard1Home}
                onAwayScoreChange={setCard1Away}
              />

              <MatchPredictionCard
                status="locked"
                metaLabel="● En direct · 62'"
                homeTeam={{ name: "Brésil", flagGradient: FLAG_BRAZIL }}
                awayTeam={{ name: "Portugal", flagGradient: FLAG_PORTUGAL }}
                homeScore={1}
                awayScore={1}
                lockedNote="Votre prono est verrouillé depuis le coup d'envoi"
              />

              <MatchPredictionCard
                status="graded"
                metaLabel="Terminé · hier"
                homeTeam={{ name: "Espagne", flagGradient: FLAG_SPAIN }}
                awayTeam={{ name: "Allemagne", flagGradient: FLAG_GERMANY }}
                homeScore={2}
                awayScore={1}
                isExactScore
                resultLabel="Score exact trouvé ✓"
                pointsVariant="exact"
                pointsLabel="+3 pts"
              />
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between px-0.5 pb-3.5 pt-1.5">
              <span className="text-[15px] font-bold">{KNOCKOUT_TITLES[phase]}</span>
              <span className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-secondary">
                Élimination directe
              </span>
            </div>

            <MatchPredictionCard
              status="editable"
              metaLabel="Coup d'envoi · 20:00"
              homeTeam={{ name: "Pays-Bas", flagGradient: FLAG_NETHERLANDS }}
              awayTeam={{ name: "Croatie", flagGradient: FLAG_CROATIA }}
              homeScore={koHome}
              awayScore={koAway}
              onHomeScoreChange={setKoHome}
              onAwayScoreChange={setKoAway}
              qualifier={{
                options: [
                  { id: "NL", label: "Pays-Bas", flagGradient: FLAG_NETHERLANDS },
                  { id: "CRO", label: "Croatie", flagGradient: FLAG_CROATIA },
                ],
                value: qualifier,
                onChange: setQualifier,
              }}
            />

            <div className="num px-2 pt-2 text-center text-xs text-ink-secondary">
              Score exact +3 pts · Bon vainqueur +1 pt
            </div>
          </div>
        )}
      </main>

      <div className="sticky bottom-0">
        <BottomNav active="matchs" />
      </div>
    </div>
  );
}
