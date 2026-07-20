import { useEffect, useState } from "react";
import { FinishedMatchDuelCard, MatchPredictionCard, type MatchTeamInfo, type QualifierOption } from "./ui";
import { buildDuelCardSides } from "../lib/duelCard";
import { useMyDuel } from "../hooks/useMyDuel";
import { useSavePrediction } from "../hooks/useSavePrediction";
import { deriveMatchStatus } from "../lib/matchStatus";
import { frenchTeamName } from "../lib/teamNamesFr";
import type { MatchRead, PredictionRead } from "../types/api";

const KICKOFF_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function toTeamInfo(team: MatchRead["home_team"]): MatchTeamInfo | null {
  if (!team) return null;
  return { name: frenchTeamName(team.name), fifaCode: team.fifa_code, flagUrl: team.flag_url };
}

/**
 * Valeur du sélecteur de qualifié pour un pronostic existant. Deux formes côté API :
 * par équipe (id numérique en chaîne) ou par côté ("home"/"away", pronostic posé quand
 * les équipes étaient des placeholders). Si les équipes sont connues depuis, le côté
 * est projeté sur l'équipe correspondante — le pronostic est conservé, l'écran affiche
 * les vraies équipes.
 */
function initialQualifier(prediction: PredictionRead | undefined, match: MatchRead): string | null {
  if (!prediction) return null;
  if (prediction.predicted_winner_team_id != null) return String(prediction.predicted_winner_team_id);
  if (prediction.predicted_winner_side != null) {
    const teamsKnown = match.home_team !== null && match.away_team !== null;
    if (!teamsKnown) return prediction.predicted_winner_side;
    return prediction.predicted_winner_side === "home" ? String(match.home_team!.id) : String(match.away_team!.id);
  }
  return null;
}

interface PredictionMatchCardProps {
  match: MatchRead;
  existingPrediction: PredictionRead | undefined;
}

export function PredictionMatchCard({ match, existingPrediction }: PredictionMatchCardProps) {
  const savePrediction = useSavePrediction();
  const duelQuery = useMyDuel();

  const [homeScore, setHomeScore] = useState(
    existingPrediction ? String(existingPrediction.predicted_home_score) : ""
  );
  const [awayScore, setAwayScore] = useState(
    existingPrediction ? String(existingPrediction.predicted_away_score) : ""
  );
  const [qualifier, setQualifier] = useState<string | null>(() => initialQualifier(existingPrediction, match));
  const [justSaved, setJustSaved] = useState(false);

  // Resynchronise les champs si la prédiction existante arrive/évolue après le premier rendu
  // (ex : requête /predictions/me terminée après le montage de la carte).
  useEffect(() => {
    if (existingPrediction) {
      setHomeScore(String(existingPrediction.predicted_home_score));
      setAwayScore(String(existingPrediction.predicted_away_score));
      setQualifier(initialQualifier(existingPrediction, match));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existingPrediction?.id]);

  const homeTeam = toTeamInfo(match.home_team);
  const awayTeam = toTeamInfo(match.away_team);
  const teamsKnown = homeTeam !== null && awayTeam !== null;
  const isKnockout = match.phase !== "group";
  const status = deriveMatchStatus(match);

  const homeNum = Number(homeScore);
  const awayNum = Number(awayScore);
  const scoresValid =
    homeScore !== "" &&
    awayScore !== "" &&
    Number.isInteger(homeNum) &&
    homeNum >= 0 &&
    Number.isInteger(awayNum) &&
    awayNum >= 0;
  const qualifierValid = !isKnockout || qualifier !== null;

  function handleSave() {
    if (!scoresValid || !qualifierValid) return;
    const qualifierIsSide = qualifier === "home" || qualifier === "away";
    savePrediction.mutate(
      {
        existingId: existingPrediction?.id ?? null,
        matchId: match.id,
        predictedHomeScore: homeNum,
        predictedAwayScore: awayNum,
        predictedWinnerTeamId: isKnockout && qualifier && !qualifierIsSide ? Number(qualifier) : null,
        predictedWinnerSide: isKnockout && qualifierIsSide ? (qualifier as "home" | "away") : null,
      },
      {
        onSuccess: () => {
          setJustSaved(true);
          setTimeout(() => setJustSaved(false), 2500);
        },
      }
    );
  }

  // Équipes connues : choix par équipe (id). Placeholders : choix par côté, libellés
  // résolus côté serveur (« Vainqueur du match 101 »).
  const qualifierOptions: readonly [QualifierOption, QualifierOption] | undefined =
    status === "editable" && isKnockout
      ? teamsKnown
        ? [
            { id: String(match.home_team!.id), label: homeTeam!.name, fifaCode: homeTeam!.fifaCode, flagUrl: homeTeam!.flagUrl },
            { id: String(match.away_team!.id), label: awayTeam!.name, fifaCode: awayTeam!.fifaCode, flagUrl: awayTeam!.flagUrl },
          ]
        : [
            {
              id: "home",
              label: (match.home_team ? frenchTeamName(match.home_team.name) : null) ?? match.home_placeholder_label ?? "Équipe à domicile",
              labelShort: match.home_placeholder_label_short ?? undefined,
              fifaCode: match.home_team?.fifa_code,
              flagUrl: match.home_team?.flag_url,
            },
            {
              id: "away",
              label: (match.away_team ? frenchTeamName(match.away_team.name) : null) ?? match.away_placeholder_label ?? "Équipe à l'extérieur",
              labelShort: match.away_placeholder_label_short ?? undefined,
              fifaCode: match.away_team?.fifa_code,
              flagUrl: match.away_team?.flag_url,
            },
          ]
      : undefined;

  const metaLabel =
    status === "locked"
      ? match.status === "live"
        ? "● En direct"
        : `Terminé · ${KICKOFF_FORMATTER.format(new Date(match.kickoff_at))}`
      : `Coup d'envoi · ${KICKOFF_FORMATTER.format(new Date(match.kickoff_at))}`;

  const lockedNote = existingPrediction
    ? "Votre prono est verrouillé depuis le coup d'envoi"
    : "Vous n'avez pas pronostiqué ce match";

  const isFinished = match.status === "finished" && match.home_score !== null && match.away_score !== null;

  if (isFinished) {
    const duelEntry = duelQuery.data?.results.find((r) => r.match_id === match.id);
    const duelStatus: "loading" | "error" | "ready" = duelQuery.isLoading ? "loading" : duelQuery.isError ? "error" : "ready";
    const { user, ai } = duelEntry ? buildDuelCardSides(duelEntry) : { user: null, ai: null };

    return (
      <FinishedMatchDuelCard
        metaLabel={metaLabel}
        homeTeam={homeTeam}
        awayTeam={awayTeam}
        homePlaceholder={match.home_placeholder_label ?? match.home_placeholder}
        awayPlaceholder={match.away_placeholder_label ?? match.away_placeholder}
        homeScore={match.home_score!}
        awayScore={match.away_score!}
        duelStatus={duelStatus}
        user={user}
        ai={ai}
      />
    );
  }

  return (
    <MatchPredictionCard
      status={status}
      metaLabel={metaLabel}
      homeTeam={homeTeam}
      awayTeam={awayTeam}
      homePlaceholder={match.home_placeholder_label ?? match.home_placeholder}
      awayPlaceholder={match.away_placeholder_label ?? match.away_placeholder}
      homeScore={status === "editable" ? homeScore : (existingPrediction?.predicted_home_score ?? "–")}
      awayScore={status === "editable" ? awayScore : (existingPrediction?.predicted_away_score ?? "–")}
      onHomeScoreChange={setHomeScore}
      onAwayScoreChange={setAwayScore}
      lockedNote={lockedNote}
      qualifier={
        qualifierOptions
          ? { options: qualifierOptions, value: qualifier, onChange: setQualifier }
          : undefined
      }
      onSave={status === "editable" ? handleSave : undefined}
      saveDisabled={!scoresValid || !qualifierValid}
      isSaving={savePrediction.isPending}
      saveError={savePrediction.isError ? savePrediction.error.message : null}
      justSaved={justSaved}
    />
  );
}
