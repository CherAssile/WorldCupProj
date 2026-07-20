import { useState } from "react";
import { TrainingMatchCard, type TrainingTeamInfo } from "./ui";
import { useSubmitTrainingPrediction } from "../hooks/useSubmitTrainingPrediction";
import { frenchTeamName } from "../lib/teamNamesFr";
import type { MatchPhase, TrainingMatchRead, TrainingMatchResultRead } from "../types/api";

const PHASE_LABELS: Record<MatchPhase, string> = {
  group: "Groupes",
  round_of_32: "32es",
  round_of_16: "8es",
  quarter_final: "Quarts",
  semi_final: "Demies",
  third_place: "Petite finale",
  final: "Finale",
};

const DOUBLED_PHASES = new Set<MatchPhase>(["quarter_final", "semi_final", "third_place", "final"]);

function toTeamInfo(team: TrainingMatchRead["home_team"]): TrainingTeamInfo {
  return { name: frenchTeamName(team.name), fifaCode: team.fifa_code, flagUrl: team.flag_url };
}

interface TrainingMatchSlotProps {
  sessionId: number;
  match: TrainingMatchRead;
  index: number;
  total: number;
  result: TrainingMatchResultRead | undefined;
}

export function TrainingMatchSlot({ sessionId, match, index, total, result }: TrainingMatchSlotProps) {
  const submitPrediction = useSubmitTrainingPrediction();
  const [homeScore, setHomeScore] = useState("");
  const [awayScore, setAwayScore] = useState("");

  const homeNum = Number(homeScore);
  const awayNum = Number(awayScore);
  const scoresValid =
    homeScore !== "" &&
    awayScore !== "" &&
    Number.isInteger(homeNum) &&
    homeNum >= 0 &&
    Number.isInteger(awayNum) &&
    awayNum >= 0;

  const doubled = DOUBLED_PHASES.has(match.phase) ? " · ×2" : "";
  const metaLabel = `Match ${index + 1}/${total} · CM ${match.edition_year} · ${PHASE_LABELS[match.phase]}${doubled}`;

  function handleSubmit() {
    if (!scoresValid) return;
    submitPrediction.mutate({
      sessionId,
      matchId: match.historical_match_id,
      body: { predicted_home_score: homeNum, predicted_away_score: awayNum },
    });
  }

  return (
    <TrainingMatchCard
      metaLabel={metaLabel}
      homeTeam={toTeamInfo(match.home_team)}
      awayTeam={toTeamInfo(match.away_team)}
      state={
        result
          ? {
              kind: "revealed",
              actualHomeScore: result.home_score,
              actualAwayScore: result.away_score,
              userHomeScore: result.predicted_home_score,
              userAwayScore: result.predicted_away_score,
              userPoints: result.user_points,
              aiHomeScore: result.ai_predicted_home_score,
              aiAwayScore: result.ai_predicted_away_score,
              aiPoints: result.ai_points,
            }
          : {
              kind: "editable",
              homeScore,
              awayScore,
              onHomeScoreChange: setHomeScore,
              onAwayScoreChange: setAwayScore,
              onSubmit: handleSubmit,
              isSubmitting: submitPrediction.isPending,
              submitError: submitPrediction.isError ? submitPrediction.error.message : null,
              canSubmit: scoresValid,
            }
      }
    />
  );
}
