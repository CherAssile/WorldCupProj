from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models.ai_prediction import AiPrediction
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.duel import DuelSummaryRead, MatchDuelRead
from app.services import scoring

router = APIRouter(prefix="/me", tags=["duel"])


def _build_match_duel(
    match: Match, prediction: Prediction | None, ai_prediction: AiPrediction | None
) -> MatchDuelRead:
    user_breakdown = scoring.score_match_prediction_breakdown(prediction, match) if prediction else None
    ai_breakdown = scoring.score_ai_match_prediction_breakdown(ai_prediction, match) if ai_prediction else None
    doubled = match.phase in scoring.DOUBLED_PHASES

    return MatchDuelRead(
        match_id=match.id,
        num=match.num,
        phase=match.phase,
        kickoff_at=match.kickoff_at,
        home_team=match.home_team,
        away_team=match.away_team,
        home_score=match.home_score,
        away_score=match.away_score,
        winner_team=match.winner_team,
        user_predicted_home_score=prediction.predicted_home_score if prediction else None,
        user_predicted_away_score=prediction.predicted_away_score if prediction else None,
        user_predicted_winner_team_id=prediction.predicted_winner_team_id if prediction else None,
        user_predicted_winner_side=prediction.predicted_winner_side if prediction else None,
        user_score_points=user_breakdown.score_points if user_breakdown else None,
        user_qualifier_points=user_breakdown.qualifier_points if user_breakdown else None,
        user_points=user_breakdown.total if user_breakdown else None,
        ai_predicted_home_score=ai_prediction.predicted_home_score if ai_prediction else None,
        ai_predicted_away_score=ai_prediction.predicted_away_score if ai_prediction else None,
        ai_points=ai_breakdown.total if ai_breakdown else None,
        ai_is_fallback=ai_prediction.is_fallback if ai_prediction else None,
        doubled=doubled,
    )


@router.get("/duel-ia", response_model=DuelSummaryRead)
def get_my_duel_vs_ai(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DuelSummaryRead:
    """Duel cumulé de l'utilisateur contre l'IA, mode compétitif -- une LECTURE des mêmes
    données que le classement général (predictions, ai_predictions, Match), agrégées
    différemment. N'écrit jamais dans scores ni le classement (cf. CLAUDE.md :
    isolation stricte, le classement général reste global et unique, IA comprise).

    Les totaux ne portent que sur les manches où les deux ont pronostiqué ; `results`
    liste en plus tous les matchs terminés (y compris non pronostiqués par
    l'utilisateur), pour l'affichage détaillé écran par écran."""
    finished_matches = [match for match in crud.match.list_all(db) if match.home_score is not None]
    predictions_by_match = {p.match_id: p for p in crud.prediction.list_by_user(db, current_user.id)}
    ai_predictions_by_match = {ap.match_id: ap for ap in crud.ai_prediction.list_all(db)}

    results: list[MatchDuelRead] = []
    user_total = ai_total = 0
    user_ahead = ai_ahead = tied = compared = 0

    for match in finished_matches:
        prediction = predictions_by_match.get(match.id)
        ai_prediction = ai_predictions_by_match.get(match.id)
        duel = _build_match_duel(match, prediction, ai_prediction)
        results.append(duel)

        if duel.user_points is not None and duel.ai_points is not None:
            user_total += duel.user_points
            ai_total += duel.ai_points
            compared += 1
            if duel.user_points > duel.ai_points:
                user_ahead += 1
            elif duel.ai_points > duel.user_points:
                ai_ahead += 1
            else:
                tied += 1

    return DuelSummaryRead(
        user_total_points=user_total,
        ai_total_points=ai_total,
        gap=user_total - ai_total,
        matches_compared=compared,
        matches_user_ahead=user_ahead,
        matches_ai_ahead=ai_ahead,
        matches_tied=tied,
        results=results,
    )
