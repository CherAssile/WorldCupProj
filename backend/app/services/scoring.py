"""Barème du mode compétitif et mise à jour de la table `scores`.

Barème :
- score exact (temps réglementaire)                         : 3 pts
- issue correcte (1/N/2) sans le score exact                : 1 pt
- bon qualifié (phases finales uniquement), cumulable        : 2 pts
- coefficient x2 à partir des quarts de finale, sur le total du match
- récompense correcte                                        : 5 pts

Le score se compare à home_score/away_score (temps réglementaire), jamais à la
prolongation ni aux tirs au but. Le qualifié se compare à winner_team_id, qui lui
tient compte des prolongations et tirs au but. Un pronostic peut donc être exact sur
l'un et faux sur l'autre : les deux composantes sont calculées indépendamment.

Pas de classement Redis ici, uniquement le calcul et l'écriture dans `scores`.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.award import Award
from app.models.award_prediction import AwardPrediction
from app.models.enums import MatchPhase, PredictedWinnerSide
from app.models.historical_match import HistoricalMatch
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.score import Score

EXACT_SCORE_POINTS = 3
CORRECT_OUTCOME_POINTS = 1
CORRECT_QUALIFIER_POINTS = 2
CORRECT_AWARD_POINTS = 5
DOUBLED_PHASES = frozenset(
    {MatchPhase.QUARTER_FINAL, MatchPhase.SEMI_FINAL, MatchPhase.THIRD_PLACE, MatchPhase.FINAL}
)


def _outcome(home_score: int, away_score: int) -> str:
    """"1" (victoire à domicile), "N" (nul) ou "2" (victoire à l'extérieur)."""
    if home_score > away_score:
        return "1"
    if away_score > home_score:
        return "2"
    return "N"


def is_exact_score(prediction: Prediction, match: Match) -> bool:
    """Score exact au temps réglementaire. False si le match n'est pas encore joué."""
    return (
        match.home_score is not None
        and match.away_score is not None
        and prediction.predicted_home_score == match.home_score
        and prediction.predicted_away_score == match.away_score
    )


def _points_for_score_guess(predicted_home: int, predicted_away: int, actual_home: int, actual_away: int) -> int:
    """Score exact (3) OU issue correcte sans score exact (1), sinon 0. Primitive commune
    au compétitif et à l'entraînement (même barème, cf. CLAUDE.md)."""
    if (predicted_home, predicted_away) == (actual_home, actual_away):
        return EXACT_SCORE_POINTS
    if _outcome(predicted_home, predicted_away) == _outcome(actual_home, actual_away):
        return CORRECT_OUTCOME_POINTS
    return 0


def _score_points(prediction: Prediction, match: Match) -> int:
    if match.home_score is None or match.away_score is None:
        return 0
    return _points_for_score_guess(
        prediction.predicted_home_score, prediction.predicted_away_score, match.home_score, match.away_score
    )


def _qualifier_points(prediction: Prediction, match: Match) -> int:
    """Uniquement en phase finale (le qualifié n'existe pas en poule). Deux formes :
    par équipe (predicted_winner_team_id), ou par côté (predicted_winner_side) pour un
    pronostic posé quand les équipes étaient encore des placeholders — le côté se résout
    ici, au calcul, une fois le match joué et ses équipes connues."""
    if match.phase == MatchPhase.GROUP:
        return 0
    if match.winner_team_id is None:
        return 0

    if prediction.predicted_winner_team_id is not None:
        return CORRECT_QUALIFIER_POINTS if prediction.predicted_winner_team_id == match.winner_team_id else 0

    if prediction.predicted_winner_side is not None:
        predicted_team_id = (
            match.home_team_id
            if prediction.predicted_winner_side == PredictedWinnerSide.HOME
            else match.away_team_id
        )
        return (
            CORRECT_QUALIFIER_POINTS
            if predicted_team_id is not None and predicted_team_id == match.winner_team_id
            else 0
        )

    return 0


def score_match_prediction(prediction: Prediction, match: Match) -> int:
    """Points d'un pronostic de match : score + qualifié (cumulables), puis coefficient
    de phase finale appliqué au total du match."""
    points = _score_points(prediction, match) + _qualifier_points(prediction, match)
    if match.phase in DOUBLED_PHASES:
        points *= 2
    return points


def score_award_prediction(prediction: AwardPrediction, award: Award) -> int:
    """Points d'un pronostic de récompense. 0 si la récompense n'est pas encore décidée."""
    if award.actual_player_id is None:
        return 0
    return CORRECT_AWARD_POINTS if prediction.predicted_player_id == award.actual_player_id else 0


def score_training_guess(predicted_home: int, predicted_away: int, match: HistoricalMatch) -> int:
    """Points d'un pronostic d'entraînement (utilisateur OU IA) contre un match historique.

    Même barème de score que le compétitif (même primitive), avec le même coefficient de
    phase finale. Pas de volet qualifié : l'entraînement ne porte que sur le score, il n'y
    a pas de vainqueur à élimination directe pronostiqué (training_predictions n'a pas ce
    champ)."""
    points = _points_for_score_guess(predicted_home, predicted_away, match.home_score, match.away_score)
    if match.phase in DOUBLED_PHASES:
        points *= 2
    return points


@dataclass
class _UserTotals:
    points: int = 0
    exact_scores: int = 0


@dataclass
class SyncResult:
    users_updated: int = 0


def sync_scores(db: Session) -> SyncResult:
    """Recalcule entièrement scores.total_points et exact_scores_count pour tous les
    utilisateurs ayant un pronostic. Idempotent : un recalcul complet à chaque appel,
    à lancer après toute synchronisation des résultats (matchs, récompenses)."""
    totals: dict[int, _UserTotals] = defaultdict(_UserTotals)

    match_rows = db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(Match.home_score.is_not(None), Match.away_score.is_not(None))
    ).all()
    for prediction, match in match_rows:
        user_totals = totals[prediction.user_id]
        user_totals.points += score_match_prediction(prediction, match)
        if is_exact_score(prediction, match):
            user_totals.exact_scores += 1

    award_rows = db.execute(
        select(AwardPrediction, Award)
        .join(Award, AwardPrediction.award_id == Award.id)
        .where(Award.actual_player_id.is_not(None))
    ).all()
    for award_prediction, award in award_rows:
        totals[award_prediction.user_id].points += score_award_prediction(award_prediction, award)

    existing_scores = {score.user_id: score for score in db.execute(select(Score)).scalars()}
    all_user_ids = set(totals) | set(existing_scores)

    for user_id in all_user_ids:
        user_totals = totals.get(user_id, _UserTotals())
        score = existing_scores.get(user_id)
        if score is None:
            db.add(
                Score(
                    user_id=user_id,
                    total_points=user_totals.points,
                    exact_scores_count=user_totals.exact_scores,
                )
            )
        else:
            score.total_points = user_totals.points
            score.exact_scores_count = user_totals.exact_scores

    db.commit()
    return SyncResult(users_updated=len(all_user_ids))
