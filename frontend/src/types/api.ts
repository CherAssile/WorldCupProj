// Types dérivés du schéma réel exposé par le backend (http://localhost:8000/openapi.json).
// Champs et nullabilité alignés terme à terme sur les schémas Pydantic — pas de faux positifs
// TypeScript qui masqueraient un champ réellement optionnel/nullable côté API.

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type MatchPhase =
  | "group"
  | "round_of_32"
  | "round_of_16"
  | "quarter_final"
  | "semi_final"
  | "third_place"
  | "final";

export type MatchStatus = "scheduled" | "live" | "finished";

export type AwardCategory = "top_scorer" | "top_assist" | "best_player";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface UserRead {
  id: number;
  email: string;
  username: string;
  is_admin: boolean;
  is_ai: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ---------------------------------------------------------------------------
// Équipes & joueurs
// ---------------------------------------------------------------------------

export interface TeamRead {
  id: number;
  name: string;
  fifa_code: string;
  flag_url: string | null;
  group_name: string | null;
  coach_name: string | null;
  coach_photo_url: string | null;
}

export interface PlayerRead {
  id: number;
  name: string;
  position: string | null;
  shirt_number: number | null;
  team: TeamRead;
}

export interface TeamPlayersGroup {
  team: TeamRead;
  players: PlayerRead[];
}

// ---------------------------------------------------------------------------
// Matchs (compétitif)
// ---------------------------------------------------------------------------

export interface MatchRead {
  id: number;
  num: number | null;
  phase: MatchPhase;
  status: MatchStatus;
  kickoff_at: string;
  home_team: TeamRead | null;
  away_team: TeamRead | null;
  home_placeholder: string | null;
  away_placeholder: string | null;
  home_score: number | null;
  away_score: number | null;
  extra_time_home_score: number | null;
  extra_time_away_score: number | null;
  penalties_home_score: number | null;
  penalties_away_score: number | null;
  winner_team: TeamRead | null;
}

export interface MatchPhaseGroup {
  phase: MatchPhase;
  matches: MatchRead[];
}

export interface AiPredictionRead {
  id: number;
  match_id: number;
  predicted_home_score: number;
  predicted_away_score: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Pronostics (compétitif)
// ---------------------------------------------------------------------------

export interface PredictionRead {
  id: number;
  user_id: number;
  match_id: number;
  predicted_home_score: number;
  predicted_away_score: number;
  predicted_winner_team_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface PredictionCreate {
  match_id: number;
  predicted_home_score: number;
  predicted_away_score: number;
  predicted_winner_team_id?: number | null;
}

export interface PredictionUpdate {
  predicted_home_score: number;
  predicted_away_score: number;
  predicted_winner_team_id?: number | null;
}

// ---------------------------------------------------------------------------
// Récompenses
// ---------------------------------------------------------------------------

export interface AwardRead {
  id: number;
  category: AwardCategory;
  lock_at: string;
  actual_player_id: number | null;
  actual_player: PlayerRead | null;
}

export interface AwardPredictionRead {
  id: number;
  user_id: number;
  award_id: number;
  predicted_player_id: number;
  predicted_player: PlayerRead;
  created_at: string;
}

export interface AwardPredictionCreate {
  award_id: number;
  predicted_player_id: number;
}

// ---------------------------------------------------------------------------
// Classement
// ---------------------------------------------------------------------------

export interface LeaderboardEntryRead {
  rank: number;
  user_id: number;
  username: string;
  is_ai: boolean;
  total_points: number;
  exact_scores_count: number;
}

export interface LeaderboardRecomputeResult {
  users_ranked: number;
}

// ---------------------------------------------------------------------------
// Entraînement — le vrai score n'apparaît jamais dans TrainingMatchRead
// (anti-triche), seulement dans TrainingMatchResultRead après soumission.
// ---------------------------------------------------------------------------

export interface TrainingMatchRead {
  historical_match_id: number;
  position: number;
  home_team: TeamRead;
  away_team: TeamRead;
  edition_year: number;
  phase: MatchPhase;
  played_at: string;
}

export interface TrainingSessionRead {
  id: number;
  started_at: string;
  completed_at: string | null;
  matches: TrainingMatchRead[];
}

export interface TrainingSessionCreate {
  match_count?: number;
}

export interface TrainingPredictionCreate {
  predicted_home_score: number;
  predicted_away_score: number;
}

export interface TrainingMatchResultRead {
  historical_match_id: number;
  home_team: TeamRead;
  away_team: TeamRead;
  home_score: number;
  away_score: number;
  predicted_home_score: number;
  predicted_away_score: number;
  ai_predicted_home_score: number;
  ai_predicted_away_score: number;
  user_points: number;
  ai_points: number;
}

export interface TrainingSessionResultsRead {
  session_id: number;
  completed: boolean;
  results: TrainingMatchResultRead[];
  user_total_points: number;
  ai_total_points: number;
}

// ---------------------------------------------------------------------------
// Erreurs FastAPI
// ---------------------------------------------------------------------------

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}
