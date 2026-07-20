from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.ai_prediction import AiPrediction
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.team import Team
from app.services import seed as seed_service
from app.services.football_api import DEFAULT_FALLBACK_PATH, FootballApiClient


def _clear_real_calendar(db_session: Session) -> None:
    """Repart d'une base sans match réel : ce module peut avoir déjà résolu de vraies
    demi-finales/finale via un précédent run_seed sur cette même base (persistant, hors de
    la transaction de test) -- un test sur "le calendrier réel" doit ignorer cet état
    avancé, pas en dépendre. Purge predictions/ai_predictions d'abord (FK vers matches),
    sans effet hors de la transaction de test (même schéma que test_ai_predictions.py)."""
    db_session.query(Prediction).delete()
    db_session.query(AiPrediction).delete()
    db_session.query(Match).delete()
    db_session.flush()

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "worldcup_test.json"

# Correspond au match "Quarter-final" France vs Spain du fixture (2026-06-20, 18:00 UTC-4).
# Date fabriquée, hors du vrai calendrier 2026 : ne peut pas coïncider avec un match réel
# déjà importé par services/seed.py sur la même base.
FIXTURE_QUARTER_FINAL_KICKOFF = datetime(2026, 6, 20, 22, 0, tzinfo=timezone.utc)


@pytest.fixture()
def unreachable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simule un réseau indisponible : tout appel doit passer par le repli local."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.football_api.httpx.get", _raise)


@pytest.fixture()
def local_fixture_client(unreachable_network: None) -> FootballApiClient:
    return FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=FIXTURE_PATH)


def test_seed_falls_back_to_local_copy_on_network_failure(
    db_session: Session, local_fixture_client: FootballApiClient
) -> None:
    """Si le téléchargement échoue, le repli local est utilisé : le seed importe bien ses matchs.

    Le fixture contient 4 équipes réelles et 4 matchs. La finale référence des équipes non
    encore résolues ("W9998"/"W9999" -- numéros volontairement inexistants pour qu'ils ne
    puissent jamais être résolus, cf. test dédié à la résolution effective plus bas) : elle
    est importée quand même, avec les FK à NULL et le placeholder renseigné (bracket),
    plutôt que d'être ignorée.
    """
    result = seed_service.run_seed(db_session, client=local_fixture_client)
    assert result.matches_created == 4

    imported = db_session.query(Match).filter(Match.kickoff_at == FIXTURE_QUARTER_FINAL_KICKOFF).one_or_none()
    assert imported is not None
    assert (imported.home_score, imported.away_score) == (1, 1)

    final = db_session.query(Match).filter(Match.num == 9002).one_or_none()
    assert final is not None
    assert (final.home_team_id, final.away_team_id) == (None, None)
    assert (final.home_placeholder, final.away_placeholder) == ("W9998", "W9999")

    team_names = {
        t.name for t in db_session.query(Team).filter(Team.name.in_(["France", "Brazil", "Spain", "Argentina"]))
    }
    assert team_names == {"France", "Brazil", "Spain", "Argentina"}


def test_full_seed_produces_104_matches_with_two_unresolved(
    db_session: Session, unreachable_network: None
) -> None:
    """Le vrai calendrier 2026 (copie locale) compte 104 matchs, dont 2 pas encore résolus
    (finale, match pour la 3e place) : équipes à NULL, placeholder renseigné.

    La copie locale (fallback_path) est un instantané figé où les demi-finales n'ont pas
    encore de score : contrairement au vrai flux live, cette source ne permet donc jamais
    de résoudre la finale/petite finale -- ce que ce test vérifie précisément. Repart d'un
    calendrier vide pour ne pas dépendre d'un état déjà avancé par un run_seed antérieur
    sur cette même base (le vrai calendrier live, lui, peut avoir progressé)."""
    _clear_real_calendar(db_session)
    client = FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=DEFAULT_FALLBACK_PATH)
    seed_service.run_seed(db_session, client=client)

    assert db_session.query(Match).count() == 104

    unresolved = db_session.query(Match).filter(Match.home_team_id.is_(None)).all()
    assert len(unresolved) == 2
    assert all(m.away_team_id is None for m in unresolved)
    assert all(m.home_placeholder and m.away_placeholder for m in unresolved)


def test_penalty_shootout_winner_is_correctly_resolved(db_session: Session, unreachable_network: None) -> None:
    """Coupe du Monde 2026, match 74 (Allemagne-Paraguay) : nul 1-1 aux 90 minutes et en
    prolongation, qualification du Paraguay aux tirs au but (3-4).

    home_score/away_score doivent rester le score du temps réglementaire (1-1) : seul lui
    sert au scoring des pronostics, quelle que soit l'issue finale du match.
    """
    client = FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=DEFAULT_FALLBACK_PATH)
    seed_service.run_seed(db_session, client=client)

    match = db_session.query(Match).filter(Match.num == 74).one()
    assert (match.home_score, match.away_score) == (1, 1)
    assert (match.extra_time_home_score, match.extra_time_away_score) == (1, 1)
    assert (match.penalties_home_score, match.penalties_away_score) == (3, 4)
    assert match.winner_team.name == "Paraguay"


def test_seed_is_idempotent(db_session: Session, local_fixture_client: FootballApiClient) -> None:
    """Deux exécutions successives sur la même source ne créent aucun doublon.

    N'suppose pas une base vide au départ (le calendrier réel peut déjà être importé) :
    compare l'état après la 1ère exécution à l'état après la 2e, en delta.
    """
    seed_service.run_seed(db_session, client=local_fixture_client)
    teams_after_first = db_session.query(Team).count()
    matches_after_first = db_session.query(Match).count()

    second = seed_service.run_seed(db_session, client=local_fixture_client)

    assert (second.teams_created, second.matches_created, second.matches_updated) == (0, 0, 0)
    assert db_session.query(Team).count() == teams_after_first
    assert db_session.query(Match).count() == matches_after_first


def test_resolve_placeholders_cascades_and_preserves_predictions(db_session: Session) -> None:
    """Deux matchs référencés joués (avec vainqueur) : la synchro résout les équipes des
    matchs aval (finale W, petite finale L), et un pronostic par côté déjà posé survit."""
    from app.models.enums import MatchPhase, MatchStatus, PredictedWinnerSide
    from app.models.prediction import Prediction
    from app.models.user import User

    france = Team(name="Ztest France", fifa_code="ZF1")
    spain = Team(name="Ztest Spain", fifa_code="ZS1")
    england = Team(name="Ztest England", fifa_code="ZE1")
    argentina = Team(name="Ztest Argentina", fifa_code="ZA1")
    db_session.add_all([france, spain, england, argentina])
    db_session.flush()

    def _semi(num: int, home: Team, away: Team, winner: Team) -> Match:
        return Match(
            num=num, home_team_id=home.id, away_team_id=away.id, phase=MatchPhase.SEMI_FINAL,
            status=MatchStatus.FINISHED, kickoff_at=datetime(2030, 7, 14, 19, 0, tzinfo=timezone.utc),
            home_score=1, away_score=2, winner_team_id=winner.id,
        )

    semi1 = _semi(9101, france, spain, spain)  # vainqueur Spain, perdant France
    semi2 = _semi(9102, england, argentina, argentina)  # vainqueur Argentina, perdant England
    final = Match(
        num=9104, home_placeholder="W9101", away_placeholder="W9102", phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED, kickoff_at=datetime(2030, 7, 19, 19, 0, tzinfo=timezone.utc),
    )
    third = Match(
        num=9103, home_placeholder="L9101", away_placeholder="L9102", phase=MatchPhase.THIRD_PLACE,
        status=MatchStatus.SCHEDULED, kickoff_at=datetime(2030, 7, 18, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([semi1, semi2, final, third])
    db_session.flush()

    # Pronostic par côté déjà posé sur la finale (équipes encore inconnues au moment du prono).
    user = User(email="ztest-resolve@example.com", username="ztest_resolve", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    prediction = Prediction(
        user_id=user.id, match_id=final.id, predicted_home_score=2, predicted_away_score=1,
        predicted_winner_side=PredictedWinnerSide.HOME,
    )
    db_session.add(prediction)
    db_session.flush()

    resolved = seed_service._resolve_placeholders(db_session)

    assert resolved == 4  # 2 côtés × 2 matchs aval
    assert (final.home_team_id, final.away_team_id) == (spain.id, argentina.id)  # W = vainqueurs
    assert (final.home_placeholder, final.away_placeholder) == (None, None)
    assert (third.home_team_id, third.away_team_id) == (france.id, england.id)  # L = perdants

    # Le pronostic par côté survit intact : c'est tout l'intérêt de predicted_winner_side.
    db_session.refresh(prediction)
    assert prediction.predicted_winner_side == PredictedWinnerSide.HOME
    assert (prediction.predicted_home_score, prediction.predicted_away_score) == (2, 1)


def test_resolve_placeholders_skips_when_referenced_match_undecided(db_session: Session) -> None:
    """Tant que le match référencé n'a pas de vainqueur, l'aval reste en placeholder."""
    from app.models.enums import MatchPhase, MatchStatus

    semi = Match(
        num=9201, home_placeholder="W9301", away_placeholder="W9302", phase=MatchPhase.SEMI_FINAL,
        status=MatchStatus.SCHEDULED, kickoff_at=datetime(2030, 7, 14, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add(semi)
    db_session.flush()

    assert seed_service._resolve_placeholders(db_session) == 0
    assert semi.home_placeholder == "W9301"
