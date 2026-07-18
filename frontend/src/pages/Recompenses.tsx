import { useState } from "react";
import { AppTopNav } from "../components/AppTopNav";
import { AwardCard, PlayerSearchSheet, type PlayerSearchTeamGroup } from "../components/ui";
import { useAwardPredictions } from "../hooks/useAwardPredictions";
import { useAwards } from "../hooks/useAwards";
import { useChooseAwardPrediction } from "../hooks/useChooseAwardPrediction";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { usePlayerSearch } from "../hooks/usePlayerSearch";
import { getInitials } from "../lib/initials";
import type { AwardCategory, AwardRead, TeamPlayersGroup } from "../types/api";

const CATEGORY_META: Record<AwardCategory, { title: string; subtitle: string; icon: JSX.Element }> = {
  top_scorer: {
    title: "Meilleur buteur",
    subtitle: "Soulier d'Or",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 9v4h11l3.5-.7c1-.2 1.5-1 1.5-1.8 0-.9-.6-1.5-1.5-1.7L13 8V6H6C5 6 4 7 4 9Z" />
        <path d="M6 16h1M9 16h1M12 16h1M15 16h1" />
      </svg>
    ),
  },
  top_assist: {
    title: "Meilleur passeur",
    subtitle: "Roi des passes",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="5" cy="17" r="2" />
        <circle cx="19" cy="7" r="2" />
        <path d="M6.4 15.6C10 12 13 9.5 17.2 7.9" />
        <path d="M14.5 8.2l3-1 .2 3" />
      </svg>
    ),
  },
  best_player: {
    title: "Meilleur joueur",
    subtitle: "Ballon d'Or",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="11" r="8" />
        <polygon points="12,7 15,9.2 13.8,12.8 10.2,12.8 9,9.2" />
        <path d="M12 3v1.5M19 8.5l-3.2.8M17.5 16l-2.6-1.8M6.5 16l2.6-1.8M5 8.5l3.2.8M8 21h8" />
      </svg>
    ),
  },
};

const DATE_FORMATTER = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });
const DATETIME_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function toSearchGroups(apiGroups: TeamPlayersGroup[]): PlayerSearchTeamGroup[] {
  return apiGroups.map((group) => ({
    teamId: group.team.id,
    teamName: group.team.name,
    teamFlagUrl: group.team.flag_url,
    players: group.players.map((player) => ({
      id: String(player.id),
      name: player.name,
      initials: getInitials(player.name),
      position: player.position,
      shirtNumber: player.shirt_number,
    })),
  }));
}

function LoadingState() {
  return (
    <div className="flex flex-1 items-center justify-center px-5 py-16 text-sm text-ink-secondary">
      Chargement des récompenses…
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-16 text-center">
      <p className="text-sm text-danger">{message}</p>
      <button onClick={onRetry} className="rounded-2xl border border-line px-5 py-2.5 text-sm font-bold text-ink-body">
        Réessayer
      </button>
    </div>
  );
}

export function Recompenses() {
  const awardsQuery = useAwards();
  const predictionsQuery = useAwardPredictions();
  const chooseAwardPrediction = useChooseAwardPrediction();

  const [openAwardId, setOpenAwardId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebouncedValue(searchInput, 300);
  const [draftSelection, setDraftSelection] = useState<string | null>(null);
  const [draftSelectionName, setDraftSelectionName] = useState<string | null>(null);

  const searchQuery = usePlayerSearch(debouncedSearch);
  const searchGroups = toSearchGroups(searchQuery.data ?? []);

  const awards = awardsQuery.data ?? [];
  const predictions = predictionsQuery.data ?? [];
  const predictionByAwardId = new Map(predictions.map((prediction) => [prediction.award_id, prediction]));
  const openAward = awards.find((award) => award.id === openAwardId) ?? null;

  function openSelector(award: AwardRead) {
    const existing = predictionByAwardId.get(award.id);
    setOpenAwardId(award.id);
    setSearchInput("");
    setDraftSelection(existing ? String(existing.predicted_player_id) : null);
    setDraftSelectionName(existing ? existing.predicted_player.name : null);
  }

  function closeSelector() {
    setOpenAwardId(null);
    setSearchInput("");
  }

  function confirmSelection() {
    if (!openAward || !draftSelection) return;
    chooseAwardPrediction.mutate(
      { award_id: openAward.id, predicted_player_id: Number(draftSelection) },
      { onSuccess: () => closeSelector() }
    );
  }

  return (
    <div className="min-h-screen bg-app">
      <AppTopNav points={128} />

      <div className="mx-auto flex max-w-[440px] flex-1 flex-col pb-8 md:max-w-[1040px]">
        <header className="px-5 pb-1 pt-4 md:border-b md:border-white/[0.08] md:px-10 md:pb-6 md:pt-8">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Récompenses</div>
          <h1 className="mt-[3px] text-[27px] font-extrabold tracking-tight md:text-[32px]">
            <span className="md:hidden">Pronos du tournoi</span>
            <span className="hidden md:inline">Pronostics du tournoi</span>
          </h1>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-secondary md:text-sm">
            Un seul choix par catégorie, verrouillé à la date limite.
          </p>
        </header>

        {awardsQuery.isLoading ? <LoadingState /> : null}

        {awardsQuery.isError ? (
          <ErrorState
            message="Impossible de charger les récompenses. Vérifie ta connexion et réessaie."
            onRetry={() => awardsQuery.refetch()}
          />
        ) : null}

        {awardsQuery.isSuccess ? (
          <>
            {predictionsQuery.isError ? (
              <div className="mx-5 mt-[18px] rounded-2xl border border-danger/[0.3] bg-danger/[0.1] px-4 py-3 text-xs text-danger md:mx-10">
                Impossible de charger tes choix existants — les catégories peuvent apparaître vides même si tu as
                déjà choisi.
              </div>
            ) : null}

            <div className="flex flex-col gap-3.5 px-5 pb-6 pt-[18px] md:grid md:grid-cols-3 md:gap-5 md:px-10 md:pb-9 md:pt-7">
              {awards.map((award) => {
                const meta = CATEGORY_META[award.category];
                const prediction = predictionByAwardId.get(award.id);
                const locked = new Date(award.lock_at).getTime() <= Date.now();
                const selectedPlayer = prediction
                  ? {
                      name: prediction.predicted_player.name,
                      initials: getInitials(prediction.predicted_player.name),
                      position: prediction.predicted_player.position ?? "Poste inconnu",
                      teamName: prediction.predicted_player.team.name,
                      flagUrl: prediction.predicted_player.team.flag_url,
                    }
                  : undefined;

                return (
                  <AwardCard
                    key={award.id}
                    icon={meta.icon}
                    title={meta.title}
                    subtitle={meta.subtitle}
                    deadlineDate={DATE_FORMATTER.format(new Date(award.lock_at))}
                    deadlineDateTime={DATETIME_FORMATTER.format(new Date(award.lock_at))}
                    locked={locked}
                    selectedPlayer={selectedPlayer}
                    onOpenSelector={() => openSelector(award)}
                  />
                );
              })}
            </div>
          </>
        ) : null}
      </div>

      {openAward ? (
        <PlayerSearchSheet
          categoryLabel={CATEGORY_META[openAward.category].title}
          query={searchInput}
          onQueryChange={setSearchInput}
          groups={searchGroups}
          isLoading={searchQuery.isFetching}
          selectedId={draftSelection}
          selectedName={draftSelectionName}
          onSelect={(id, name) => {
            setDraftSelection(id);
            setDraftSelectionName(name);
          }}
          onConfirm={confirmSelection}
          onClose={closeSelector}
          isConfirming={chooseAwardPrediction.isPending}
          confirmError={chooseAwardPrediction.isError ? chooseAwardPrediction.error.message : null}
        />
      ) : null}
    </div>
  );
}
