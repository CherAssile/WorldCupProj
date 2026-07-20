from datetime import datetime

from pydantic import BaseModel

from app.models.enums import MatchPhase, PredictedWinnerSide
from app.schemas.team import TeamRead


class MatchDuelRead(BaseModel):
    """Une manche du duel joueur/IA : le match, les deux pronostics (s'ils existent) et
    leurs points, décomposés pour l'affichage. Un match figure ici dès qu'il est terminé,
    que l'utilisateur l'ait pronostiqué ou non -- user_points est alors None (distinct de
    0 : "pas pronostiqué" n'est pas "pronostiqué et raté")."""

    match_id: int
    num: int | None
    phase: MatchPhase
    kickoff_at: datetime
    home_team: TeamRead | None
    away_team: TeamRead | None
    home_score: int | None
    away_score: int | None
    winner_team: TeamRead | None

    user_predicted_home_score: int | None
    user_predicted_away_score: int | None
    user_predicted_winner_team_id: int | None
    user_predicted_winner_side: PredictedWinnerSide | None
    user_score_points: int | None
    user_qualifier_points: int | None
    user_points: int | None  # None = pas pronostiqué

    ai_predicted_home_score: int | None  # None = pas de pronostic IA pour ce match
    ai_predicted_away_score: int | None
    ai_points: int | None
    ai_is_fallback: bool | None

    doubled: bool  # coefficient x2 (phase finale à partir des quarts)


class DuelSummaryRead(BaseModel):
    """Duel cumulé de l'utilisateur contre l'IA, mode compétitif. Les totaux ne portent
    QUE sur les manches où les deux ont pronostiqué (une confrontation réelle) ; `results`
    liste en plus tous les matchs terminés, y compris ceux non pronostiqués par
    l'utilisateur, pour l'affichage détaillé match par match."""

    user_total_points: int
    ai_total_points: int
    gap: int  # user_total_points - ai_total_points ; positif = utilisateur devant
    matches_compared: int  # manches où les deux ont pronostiqué (comptent dans les totaux)
    matches_user_ahead: int
    matches_ai_ahead: int
    matches_tied: int
    results: list[MatchDuelRead]
