from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.award import Award
from app.models.award_prediction import AwardPrediction
from app.models.enums import AwardCategory, MatchPhase, MatchStatus
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.score import Score
from app.models.team import Team
from app.models.user import User
from app.services import scoring


def _match(phase: MatchPhase, home_score: int, away_score: int, winner_team_id: int | None = None) -> Match:
    return Match(phase=phase, home_score=home_score, away_score=away_score, winner_team_id=winner_team_id)


def _prediction(home: int, away: int, predicted_winner_team_id: int | None = None) -> Prediction:
    return Prediction(
        predicted_home_score=home, predicted_away_score=away, predicted_winner_team_id=predicted_winner_team_id
    )


def test_exact_score_scores_3_points() -> None:
    match = _match(MatchPhase.GROUP, 2, 1)
    prediction = _prediction(2, 1)
    assert scoring.score_match_prediction(prediction, match) == 3


def test_correct_outcome_without_exact_score_scores_1_point() -> None:
    match = _match(MatchPhase.GROUP, 2, 0)
    prediction = _prediction(1, 0)  # même issue (victoire à domicile), score différent
    assert scoring.score_match_prediction(prediction, match) == 1


def test_wrong_outcome_scores_0_points() -> None:
    match = _match(MatchPhase.GROUP, 2, 0)  # victoire à domicile
    prediction = _prediction(0, 1)  # victoire à l'extérieur pronostiquée
    assert scoring.score_match_prediction(prediction, match) == 0


def test_correct_qualifier_scores_2_points() -> None:
    """Issue fausse (0 pt), qualifié juste, phase non doublée (round of 16) : seuls les
    2 points du qualifié comptent."""
    match = _match(MatchPhase.ROUND_OF_16, 1, 1, winner_team_id=1)  # nul 1-1
    prediction = _prediction(2, 0, predicted_winner_team_id=1)  # victoire à domicile pronostiquée
    assert scoring.score_match_prediction(prediction, match) == 2


def test_wrong_qualifier_drops_only_the_qualifier_points() -> None:
    """Issue correcte (1 pt) mais mauvais qualifié (0 pt), phase non doublée."""
    match = _match(MatchPhase.ROUND_OF_16, 2, 1, winner_team_id=1)
    prediction = _prediction(3, 1, predicted_winner_team_id=2)  # même issue, mauvais qualifié
    assert scoring.score_match_prediction(prediction, match) == 1


def test_exact_score_and_correct_qualifier_are_cumulative() -> None:
    """Exemple CLAUDE.md : match 74, 1-1 aux tirs au but, Paraguay qualifié.
    Pronostic "1-1, Paraguay qualifié" = 3 (score exact) + 2 (bon qualifié) = 5 pts."""
    match = _match(MatchPhase.ROUND_OF_32, 1, 1, winner_team_id=39)  # Round of 32, non doublé
    prediction = _prediction(1, 1, predicted_winner_team_id=39)
    assert scoring.score_match_prediction(prediction, match) == 5


def test_quarter_final_and_beyond_doubles_the_match_total() -> None:
    """Même composition que le cumul ci-dessus, mais en quart de finale : coefficient x2."""
    match = _match(MatchPhase.QUARTER_FINAL, 1, 1, winner_team_id=39)
    prediction = _prediction(1, 1, predicted_winner_team_id=39)
    assert scoring.score_match_prediction(prediction, match) == (3 + 2) * 2


def test_unplayed_match_scores_0_points() -> None:
    match = _match(MatchPhase.GROUP, None, None)
    prediction = _prediction(1, 0)
    assert scoring.score_match_prediction(prediction, match) == 0


def test_award_prediction_correct_scores_5_points() -> None:
    award = Award(category=AwardCategory.TOP_SCORER, actual_player_id=10)
    prediction = AwardPrediction(predicted_player_id=10)
    assert scoring.score_award_prediction(prediction, award) == 5


def test_award_prediction_wrong_scores_0_points() -> None:
    award = Award(category=AwardCategory.TOP_SCORER, actual_player_id=10)
    prediction = AwardPrediction(predicted_player_id=11)
    assert scoring.score_award_prediction(prediction, award) == 0


def test_award_prediction_not_yet_decided_scores_0_points() -> None:
    award = Award(category=AwardCategory.TOP_SCORER, actual_player_id=None)
    prediction = AwardPrediction(predicted_player_id=10)
    assert scoring.score_award_prediction(prediction, award) == 0


def test_sync_scores_updates_scores_table(db_session: Session) -> None:
    """Vérifie l'écriture réelle en base, au-delà du calcul pur : crée la ligne scores,
    et reste idempotent (pas de doublon) si relancé après une resynchronisation."""
    user = User(email="sync@example.com", username="syncuser", hashed_password="x")
    home = Team(name="Sync Home", fifa_code="SYH")
    away = Team(name="Sync Away", fifa_code="SYA")
    db_session.add_all([user, home, away])
    db_session.flush()

    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.GROUP,
        status=MatchStatus.FINISHED,
        kickoff_at=datetime.now(timezone.utc),
        home_score=2,
        away_score=1,
    )
    db_session.add(match)
    db_session.flush()

    prediction = Prediction(user_id=user.id, match_id=match.id, predicted_home_score=2, predicted_away_score=1)
    db_session.add(prediction)
    db_session.flush()

    scoring.sync_scores(db_session)

    score = db_session.query(Score).filter(Score.user_id == user.id).one()
    assert score.total_points == 3
    assert score.exact_scores_count == 1

    scoring.sync_scores(db_session)
    assert db_session.query(Score).filter(Score.user_id == user.id).count() == 1
