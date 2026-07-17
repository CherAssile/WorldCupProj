import { useState } from "react";
import { AwardCard, OddsGauge, PlayerSearchSheet, RaceGauge, type AwardPlayerOption } from "../components/ui";
import { FLAG_ARGENTINA, FLAG_FRANCE } from "../lib/flagGradients";

type AwardCategory = "buteur" | "passeur" | "joueur";

const CATEGORY_LABELS: Record<AwardCategory, string> = {
  buteur: "Meilleur buteur",
  passeur: "Meilleur passeur",
  joueur: "Meilleur joueur",
};

const PLAYER_POOL: AwardPlayerOption[] = [
  { id: "km", name: "Kylian Mbappé", initials: "KM", position: "Attaquant", shirtNumber: 10, teamName: "France", teamFlagGradient: FLAG_FRANCE },
  { id: "ag", name: "Antoine Griezmann", initials: "AG", position: "Attaquant", shirtNumber: 7, teamName: "France", teamFlagGradient: FLAG_FRANCE },
  { id: "lm", name: "Lionel Messi", initials: "LM", position: "Milieu off.", shirtNumber: 10, teamName: "Argentine", teamFlagGradient: FLAG_ARGENTINA },
  { id: "ja", name: "Julián Álvarez", initials: "JA", position: "Attaquant", shirtNumber: 9, teamName: "Argentine", teamFlagGradient: FLAG_ARGENTINA },
];

function BallIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 9v4h11l3.5-.7c1-.2 1.5-1 1.5-1.8 0-.9-.6-1.5-1.5-1.7L13 8V6H6C5 6 4 7 4 9Z" />
      <path d="M6 16h1M9 16h1M12 16h1M15 16h1" />
    </svg>
  );
}

function AssistIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="17" r="2" />
      <circle cx="19" cy="7" r="2" />
      <path d="M6.4 15.6C10 12 13 9.5 17.2 7.9" />
      <path d="M14.5 8.2l3-1 .2 3" />
    </svg>
  );
}

function BallonDOrIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="11" r="8" />
      <polygon points="12,7 15,9.2 13.8,12.8 10.2,12.8 9,9.2" />
      <path d="M12 3v1.5M19 8.5l-3.2.8M17.5 16l-2.6-1.8M6.5 16l2.6-1.8M5 8.5l3.2.8M8 21h8" />
    </svg>
  );
}

export function Recompenses() {
  const [scorer, setScorer] = useState<string | null>("km");
  const [assist, setAssist] = useState<string | null>(null);
  const [bestPlayer, setBestPlayer] = useState<string | null>("lm");
  const [openCategory, setOpenCategory] = useState<AwardCategory | null>(null);
  const [draftSelection, setDraftSelection] = useState<string | null>(null);

  const findPlayer = (id: string | null) => {
    const player = PLAYER_POOL.find((candidate) => candidate.id === id);
    return player
      ? {
          name: player.name,
          initials: player.initials,
          position: player.position,
          teamName: player.teamName,
          teamFlagGradient: player.teamFlagGradient,
        }
      : undefined;
  };

  function openSelector(category: AwardCategory, currentId: string | null) {
    setOpenCategory(category);
    setDraftSelection(currentId);
  }

  function confirmSelection() {
    if (!draftSelection || !openCategory) return;
    if (openCategory === "buteur") setScorer(draftSelection);
    if (openCategory === "passeur") setAssist(draftSelection);
    if (openCategory === "joueur") setBestPlayer(draftSelection);
    setOpenCategory(null);
  }

  return (
    <div className="mx-auto min-h-screen max-w-[440px] bg-app pb-8 md:max-w-[1040px]">
      <header className="px-5 pb-1 pt-4 md:border-b md:border-white/[0.08] md:px-10 md:pb-6 md:pt-8">
        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Récompenses</div>
        <h1 className="mt-[3px] text-[27px] font-extrabold tracking-tight md:text-[32px]">
          <span className="md:hidden">Pronos du tournoi</span>
          <span className="hidden md:inline">Pronostics du tournoi</span>
        </h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-secondary md:text-sm">
          Un seul choix par catégorie, verrouillé au coup d'envoi du premier match.
        </p>
      </header>

      <div className="flex flex-col gap-3.5 px-5 pb-6 pt-[18px] md:grid md:grid-cols-3 md:gap-5 md:px-10 md:pb-9 md:pt-7">
        <AwardCard
          icon={<BallIcon />}
          title="Meilleur buteur"
          subtitle="Soulier d'Or"
          deadlineDate="11 juin"
          selectedPlayer={findPlayer(scorer)}
          onOpenSelector={() => openSelector("buteur", scorer)}
        >
          <RaceGauge
            title="Course au Soulier d'Or"
            rankBadge="1ER · 5 BUTS"
            entries={[
              { label: "Mbappé", value: 5, isLeader: true },
              { label: "Kane", value: 4 },
            ]}
          />
        </AwardCard>

        <AwardCard
          icon={<AssistIcon />}
          title="Meilleur passeur"
          subtitle="Roi des passes"
          deadlineDate="11 juin"
          selectedPlayer={findPlayer(assist)}
          onOpenSelector={() => openSelector("passeur", assist)}
        />

        <AwardCard
          icon={<BallonDOrIcon />}
          title="Meilleur joueur"
          subtitle="Ballon d'Or"
          deadlineDate="11 juin"
          selectedPlayer={findPlayer(bestPlayer)}
          onOpenSelector={() => openSelector("joueur", bestPlayer)}
        >
          <OddsGauge label="Cote actuelle" percent={72} rankBadge="2E" />
        </AwardCard>
      </div>

      {openCategory ? (
        <PlayerSearchSheet
          categoryLabel={CATEGORY_LABELS[openCategory]}
          players={PLAYER_POOL}
          totalPlayerCount={1248}
          selectedId={draftSelection}
          onSelect={setDraftSelection}
          onConfirm={confirmSelection}
          onClose={() => setOpenCategory(null)}
        />
      ) : null}
    </div>
  );
}
