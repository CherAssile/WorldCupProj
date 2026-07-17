import { useState } from "react";
import { AppBottomNav } from "../components/AppBottomNav";
import { LeaderboardRow, type LeaderboardPlayer } from "../components/ui";

const PLAYERS: LeaderboardPlayer[] = [
  { rank: 1, name: "Zizou_10", initials: "ZZ", points: 342, exactScores: 24 },
  { rank: 2, name: "La_Pulga", initials: "LP", points: 331, exactScores: 22 },
  { rank: 3, name: "RoboPronos", initials: "", points: 328, exactScores: 23, isAI: true },
  { rank: 4, name: "Kyllian_M", initials: "KM", points: 319, exactScores: 20 },
  { rank: 5, name: "TikiTaka", initials: "TT", points: 305, exactScores: 19 },
  { rank: 6, name: "Elena_S", initials: "ES", points: 298, exactScores: 18 },
  { rank: 7, name: "DeadlineDay", initials: "DD", points: 287, exactScores: 17 },
  { rank: 8, name: "GegenPress", initials: "GP", points: 279, exactScores: 16 },
  { rank: 9, name: "Catenaccio", initials: "CA", points: 268, exactScores: 15 },
  { rank: 10, name: "Panenka_K", initials: "PK", points: 261, exactScores: 14 },
];

const YOU: LeaderboardPlayer = { rank: 27, name: "Vous · Thomas", initials: "TB", points: 148, exactScores: 8 };

type LeaderboardFilter = "general" | "matchday";

export function Classement() {
  const [filter, setFilter] = useState<LeaderboardFilter>("general");

  return (
    <div className="mx-auto flex min-h-screen max-w-[440px] flex-col bg-app md:max-w-[860px]">
      <header className="px-5 pb-3.5 pt-4 md:flex md:items-end md:justify-between md:border-b md:border-white/[0.08] md:px-10 md:pb-[26px] md:pt-[34px]">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Ligue des potes · 41 joueurs
          </div>
          <h1 className="mt-[3px] text-[30px] font-extrabold tracking-tight md:mt-1.5 md:text-[34px]">
            <span className="md:hidden">Classement</span>
            <span className="hidden md:inline">Classement général</span>
          </h1>
        </div>
        <div className="mt-4 hidden gap-2.5 md:flex">
          <button
            onClick={() => setFilter("general")}
            className={`rounded-xl px-[18px] py-2.5 text-[13px] font-bold transition-colors ${
              filter === "general" ? "bg-primary text-[#06210F]" : "border border-line text-ink-secondary"
            }`}
          >
            Général
          </button>
          <button
            onClick={() => setFilter("matchday")}
            className={`rounded-xl px-[18px] py-2.5 text-[13px] font-semibold transition-colors ${
              filter === "matchday" ? "bg-primary text-[#06210F]" : "border border-line text-ink-secondary"
            }`}
          >
            Cette journée
          </button>
        </div>
      </header>

      <div className="hidden grid-cols-[64px_1fr_200px_130px] gap-4 px-10 py-3.5 text-[11px] font-bold uppercase tracking-[0.1em] text-ink-secondary md:grid">
        <span>Rang</span>
        <span>Joueur</span>
        <span className="text-right">Scores exacts</span>
        <span className="text-right">Points</span>
      </div>

      <main className="flex-1 overflow-y-auto px-4 pb-3 pt-1 md:px-6 md:pb-2 md:pt-0">
        {PLAYERS.map((player) => (
          <LeaderboardRow key={player.rank} player={player} />
        ))}
      </main>

      <div className="sticky bottom-0 border-t border-white/[0.09] bg-[#0D1424]">
        <div className="px-4 pb-3 pt-3 md:px-6 md:pb-[26px] md:pt-[14px]">
          <div className="mb-2 pl-1 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-secondary md:pl-4">
            Votre position
          </div>
          <LeaderboardRow player={YOU} highlighted />
        </div>
        <div className="md:hidden">
          <AppBottomNav />
        </div>
      </div>
    </div>
  );
}
