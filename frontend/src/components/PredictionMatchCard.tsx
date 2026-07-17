import { useEffect, useState } from "react";
import { MatchPredictionCard, type MatchTeamInfo, type QualifierOption } from "./ui";
import { useSavePrediction } from "../hooks/useSavePrediction";
import { deriveMatchStatus } from "../lib/matchStatus";
import type { MatchRead, PredictionRead } from "../types/api";

const KICKOFF_FORMATTER = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function toTeamInfo(team: MatchRead["home_team"]): MatchTeamInfo | null {
  if (!team) return null;
  return { name: team.name, fifaCode: team.fifa_code, flagUrl: team.flag_url };
}

interface PredictionMatchCardProps {
  match: MatchRead;
  existingPrediction: PredictionRead | undefined;
}

export function PredictionMatchCard({ match, existingPrediction }: PredictionMatchCardProps) {
  const savePrediction = useSavePrediction();

  const [homeScore, setHomeScore] = useState(
    existingPrediction ? String(existingPrediction.predicted_home_score) : ""
  );
  const [awayScore, setAwayScore] = useState(
    existingPrediction ? String(existingPrediction.predicted_away_score) : ""
  );
  const [qualifier, setQualifier] = useState<string | null>(
    existingPrediction?.predicted_winner_team_id != null ? String(existingPrediction.predicted_winner_team_id) : null
  );
  const [justSaved, setJustSaved] = useState(false);

  // Resynchronise les champs si la prédiction existante arrive/évolue après le premier rendu
  // (ex : requête /predictions/me terminée après le montage de la carte).
  useEffect(() => {
    if (existingPrediction) {
      setHomeScore(String(existingPrediction.predicted_home_score));
      setAwayScore(String(existingPrediction.predicted_away_score));
      setQualifier(
        existingPrediction.predicted_winner_team_id != null ? String(existingPrediction.predicted_winner_team_id) : null
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existingPrediction?.id]);

  const homeTeam = toTeamInfo(match.home_team);
  const awayTeam = toTeamInfo(match.away_team);
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
    savePrediction.mutate(
      {
        existingId: existingPrediction?.id ?? null,
        matchId: match.id,
        predictedHomeScore: homeNum,
        predictedAwayScore: awayNum,
        predictedWinnerTeamId: isKnockout && qualifier ? Number(qualifier) : null,
      },
      {
        onSuccess: () => {
          setJustSaved(true);
          setTimeout(() => setJustSaved(false), 2500);
        },
      }
    );
  }

  const qualifierOptions: readonly [QualifierOption, QualifierOption] | undefined =
    status === "editable" && isKnockout && homeTeam && awayTeam
      ? [
          { id: String(match.home_team!.id), label: homeTeam.name, fifaCode: homeTeam.fifaCode, flagUrl: homeTeam.flagUrl },
          { id: String(match.away_team!.id), label: awayTeam.name, fifaCode: awayTeam.fifaCode, flagUrl: awayTeam.flagUrl },
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

  return (
    <MatchPredictionCard
      status={status}
      metaLabel={metaLabel}
      homeTeam={homeTeam}
      awayTeam={awayTeam}
      homePlaceholder={match.home_placeholder}
      awayPlaceholder={match.away_placeholder}
      homeScore={status === "editable" ? homeScore : (existingPrediction?.predicted_home_score ?? "–")}
      awayScore={status === "editable" ? awayScore : (existingPrediction?.predicted_away_score ?? "–")}
      onHomeScoreChange={setHomeScore}
      onAwayScoreChange={setAwayScore}
      lockedNote={lockedNote}
      pendingMessage="Les équipes de ce match ne sont pas encore connues : pronostic impossible."
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
