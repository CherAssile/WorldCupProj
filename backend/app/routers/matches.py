from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.models.ai_prediction import AiPrediction
from app.models.enums import MatchPhase
from app.models.match import Match
from app.schemas.ai_prediction import AiPredictionRead
from app.schemas.lineup import LineupPlayerRead, MatchLineupsRead, TeamLineupRead
from app.schemas.match import MatchPhaseGroup, MatchRead
from app.schemas.team import TeamRead
from app.services.placeholders import resolve_placeholder

router = APIRouter(prefix="/matches", tags=["matchs"])


def _to_match_read(match: Match, matches_by_num: dict[int, Match]) -> MatchRead:
    """Sérialise un match en résolvant ses placeholders d'un niveau (« France ou Espagne »)
    contre l'ensemble des matchs, indexés par num."""
    read = MatchRead.model_validate(match)
    home = resolve_placeholder(match.home_placeholder, matches_by_num)
    away = resolve_placeholder(match.away_placeholder, matches_by_num)
    read.home_placeholder_label = home.long
    read.home_placeholder_label_short = home.short
    read.away_placeholder_label = away.long
    read.away_placeholder_label_short = away.short
    return read


@router.get("", response_model=list[MatchPhaseGroup])
def list_matches_by_phase(db: Session = Depends(get_db)) -> list[MatchPhaseGroup]:
    """Liste les matchs du tournoi, groupés par phase (ordre du tournoi)."""
    matches = crud.match.list_all(db)
    matches_by_num = {match.num: match for match in matches if match.num is not None}

    matches_by_phase: dict[MatchPhase, list[MatchRead]] = {phase: [] for phase in MatchPhase}
    for match in matches:
        matches_by_phase[match.phase].append(_to_match_read(match, matches_by_num))

    return [MatchPhaseGroup(phase=phase, matches=matches_by_phase[phase]) for phase in MatchPhase]


@router.get("/{match_id}/ai-prediction", response_model=AiPredictionRead)
def get_match_ai_prediction(match_id: int, db: Session = Depends(get_db)) -> AiPrediction:
    """Pronostic IA pour ce match, s'il a déjà été généré (voir POST /ai-predictions/regenerate)."""
    match = crud.match.get_by_id(db, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match introuvable.")

    prediction = crud.ai_prediction.get_by_match_id(db, match_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun pronostic IA pour ce match.")

    return prediction


@router.get("/{match_id}/lineups", response_model=MatchLineupsRead)
def get_match_lineups(match_id: int, db: Session = Depends(get_db)) -> MatchLineupsRead:
    """Compositions des deux équipes pour ce match.

    Les compositions ne sortent qu'environ 1h avant le coup d'envoi : leur absence est un
    état NORMAL (available=False), jamais une erreur -- seul un match introuvable renvoie
    une 404.
    """
    match = crud.match.get_by_id(db, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match introuvable.")

    lineups = crud.lineup.get_by_match(db, match_id)
    if not lineups:
        return MatchLineupsRead(match_id=match_id, available=False, message="Composition non encore annoncée.")

    by_team_id = {lineup.team_id: lineup for lineup in lineups}

    def _build(team_id: int | None) -> TeamLineupRead | None:
        lineup = by_team_id.get(team_id) if team_id is not None else None
        if lineup is None:
            return None
        return TeamLineupRead(
            team=TeamRead.model_validate(lineup.team),
            formation=lineup.formation,
            players=[
                LineupPlayerRead(
                    player_id=entry.player_id,
                    name=entry.player.name,
                    position=entry.position,
                    shirt_number=entry.shirt_number,
                    is_starter=entry.is_starter,
                )
                for entry in lineup.players
            ],
        )

    return MatchLineupsRead(
        match_id=match_id,
        available=True,
        home=_build(match.home_team_id),
        away=_build(match.away_team_id),
    )
