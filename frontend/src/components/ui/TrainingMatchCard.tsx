import { Button } from "./Button";
import { ScoreInput } from "./ScoreInput";

export interface TrainingTeamInfo {
  name: string;
  fifaCode: string;
  flagUrl: string | null;
}

type TrainingMatchCardState =
  | {
      kind: "editable";
      homeScore: string;
      awayScore: string;
      onHomeScoreChange: (value: string) => void;
      onAwayScoreChange: (value: string) => void;
      onSubmit: () => void;
      isSubmitting: boolean;
      submitError: string | null;
      canSubmit: boolean;
    }
  | {
      kind: "revealed";
      actualHomeScore: number;
      actualAwayScore: number;
      userHomeScore: number;
      userAwayScore: number;
      userPoints: number;
      aiHomeScore: number;
      aiAwayScore: number;
      aiPoints: number;
    };

interface TrainingMatchCardProps {
  metaLabel: string;
  homeTeam: TrainingTeamInfo;
  awayTeam: TrainingTeamInfo;
  state: TrainingMatchCardState;
}

function TeamBadge({ team }: { team: TrainingTeamInfo }) {
  return team.flagUrl ? (
    <img
      src={team.flagUrl}
      alt=""
      className="h-11 w-11 flex-shrink-0 rounded-full object-cover shadow-[0_0_0_2px_rgba(255,255,255,0.12)]"
    />
  ) : (
    <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-elevated text-[11px] font-extrabold text-ink-secondary shadow-[0_0_0_2px_rgba(255,255,255,0.12)]">
      {team.fifaCode}
    </div>
  );
}

function DuelRow({
  label,
  homeScore,
  awayScore,
  points,
  isWinner,
}: {
  label: string;
  homeScore: number;
  awayScore: number;
  points: number;
  isWinner: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between gap-2 rounded-xl border px-3.5 py-2.5 ${
        isWinner ? "border-primary/[0.4] bg-primary/[0.12]" : "border-transparent bg-elevated"
      }`}
    >
      <span className={`text-xs font-bold uppercase tracking-[0.06em] ${isWinner ? "text-primary-light" : "text-ink-secondary"}`}>
        {label}
      </span>
      <span className="num text-[15px] font-extrabold text-ink">
        {homeScore} – {awayScore}
      </span>
      <span
        className={`num flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-extrabold ${
          isWinner ? "bg-primary text-[#06210F]" : "bg-[#0F1729] text-ink-secondary"
        }`}
      >
        +{points} pts
      </span>
    </div>
  );
}

/** Carte de match d'entraînement : score caché + saisie avant soumission, duel toi/IA révélé après. */
export function TrainingMatchCard({ metaLabel, homeTeam, awayTeam, state }: TrainingMatchCardProps) {
  return (
    <div className="rounded-[22px] border border-white/[0.07] bg-gradient-to-b from-[#182444] to-[#131C33] p-[18px] shadow-[0_12px_30px_rgba(0,0,0,0.35)]">
      <div className="mb-4 text-xs font-semibold uppercase tracking-[0.12em] text-ink-secondary">{metaLabel}</div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <div className="flex flex-col items-center gap-2">
          <TeamBadge team={homeTeam} />
          <span className="text-center text-[13px] font-bold text-ink">{homeTeam.name}</span>
        </div>

        {state.kind === "editable" ? (
          <div className="flex items-center gap-2">
            <ScoreInput value={state.homeScore} onChange={state.onHomeScoreChange} size="sm" />
            <span className="text-base font-bold text-ink-muted">–</span>
            <ScoreInput value={state.awayScore} onChange={state.onAwayScoreChange} size="sm" />
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-muted">Score réel</span>
            <div className="num text-2xl font-extrabold text-ink">
              {state.actualHomeScore} – {state.actualAwayScore}
            </div>
          </div>
        )}

        <div className="flex flex-col items-center gap-2">
          <TeamBadge team={awayTeam} />
          <span className="text-center text-[13px] font-bold text-ink">{awayTeam.name}</span>
        </div>
      </div>

      {state.kind === "editable" ? (
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/[0.08] pt-3.5">
          <div className="min-h-[16px] flex-1 text-xs">
            {state.submitError ? <span className="text-danger">{state.submitError}</span> : null}
          </div>
          <Button variant="primary" size="sm" onClick={state.onSubmit} disabled={!state.canSubmit || state.isSubmitting}>
            {state.isSubmitting ? "Envoi…" : "Valider mon prono"}
          </Button>
        </div>
      ) : (
        <div className="mt-4 flex flex-col gap-2 border-t border-white/[0.08] pt-3.5">
          <DuelRow
            label="Toi"
            homeScore={state.userHomeScore}
            awayScore={state.userAwayScore}
            points={state.userPoints}
            isWinner={state.userPoints > state.aiPoints}
          />
          <DuelRow
            label="IA"
            homeScore={state.aiHomeScore}
            awayScore={state.aiAwayScore}
            points={state.aiPoints}
            isWinner={state.aiPoints > state.userPoints}
          />
          {state.userPoints === state.aiPoints ? (
            <div className="text-center text-[11px] font-semibold text-ink-secondary">Égalité sur ce match</div>
          ) : null}
        </div>
      )}
    </div>
  );
}
