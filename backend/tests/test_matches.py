from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.team import Team


def test_matches_grouped_by_phase_structure(client: TestClient) -> None:
    """/matches renvoie toujours une entrée par phase du tournoi, dans l'ordre canonique.

    N'suppose pas une base vide : le calendrier réel peut déjà être alimenté (services/seed.py).
    """
    response = client.get("/matches")
    assert response.status_code == 200

    body = response.json()
    assert [group["phase"] for group in body] == [phase.value for phase in MatchPhase]
    assert all(isinstance(group["matches"], list) for group in body)


def test_matches_grouped_by_phase_with_data(client: TestClient, db_session: Session) -> None:
    """Un match créé dans une phase donnée apparaît dans le bon groupe, avec les équipes imbriquées."""
    home = Team(name="Testland Alpha", fifa_code="TLA")
    away = Team(name="Testland Beta", fifa_code="TLB")
    db_session.add_all([home, away])
    db_session.flush()

    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.QUARTER_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 1, 18, 0, tzinfo=timezone.utc),
    )
    db_session.add(match)
    db_session.commit()

    response = client.get("/matches")
    assert response.status_code == 200

    group_by_phase = {group["phase"]: group["matches"] for group in response.json()}
    quarter_final_matches = group_by_phase["quarter_final"]

    created = next(m for m in quarter_final_matches if m["home_team"]["name"] == "Testland Alpha")
    assert created["away_team"]["name"] == "Testland Beta"


def _match_from_response(response_json: list, phase: str, match_id: int) -> dict:
    group_by_phase = {group["phase"]: group["matches"] for group in response_json}
    return next(m for m in group_by_phase[phase] if m["id"] == match_id)


def test_placeholder_label_resolved_one_level_when_referenced_teams_known(
    client: TestClient, db_session: Session
) -> None:
    """La demie référencée est connue → le libellé remonte d'un niveau : « France ou
    Espagne » (et « FRA/ESP » en version courte) plutôt que « Vainqueur du match 90101 »."""
    france = Team(name="Zztest France", fifa_code="ZFR")
    espagne = Team(name="Zztest Espagne", fifa_code="ZES")
    db_session.add_all([france, espagne])
    db_session.flush()

    semi = Match(
        num=90101,
        home_team_id=france.id,
        away_team_id=espagne.id,
        phase=MatchPhase.SEMI_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 14, 19, 0, tzinfo=timezone.utc),
    )
    final = Match(
        num=90201,
        home_placeholder="W90101",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 19, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([semi, final])
    db_session.commit()

    created = _match_from_response(client.get("/matches").json(), "final", final.id)
    assert created["home_placeholder_label"] == "Zztest France ou Zztest Espagne"
    assert created["home_placeholder_label_short"] == "ZFR/ZES"


def test_placeholder_label_translates_team_names_to_french(client: TestClient, db_session: Session) -> None:
    """Bug de cohérence de langue : « Spain »/« England » (noms source, anglais) doivent
    apparaître traduits dans le libellé composé (« ... ou Espagne », pas « ... ou Spain »).
    Team.name lui-même reste inchangé (contrat avec ai-service).

    Réutilise les équipes réelles (name/fifa_code uniques, déjà présentes sur cette base
    via le vrai calendrier) plutôt que d'en recréer -- create_or_get pour rester robuste
    si elles n'existaient pas encore."""
    spain = db_session.query(Team).filter(Team.name == "Spain").one_or_none()
    if spain is None:
        spain = Team(name="Spain", fifa_code="ESP")
        db_session.add(spain)
    england = db_session.query(Team).filter(Team.name == "England").one_or_none()
    if england is None:
        england = Team(name="England", fifa_code="ENG")
        db_session.add(england)
    db_session.flush()

    semi = Match(
        num=90121,
        home_team_id=spain.id,
        away_team_id=england.id,
        phase=MatchPhase.SEMI_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 14, 19, 0, tzinfo=timezone.utc),
    )
    final = Match(
        num=90221,
        home_placeholder="W90121",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 19, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([semi, final])
    db_session.commit()

    created = _match_from_response(client.get("/matches").json(), "final", final.id)
    assert created["home_placeholder_label"] == "Espagne ou Angleterre"
    assert created["home_placeholder_label_short"] == "ESP/ENG"  # codes FIFA inchangés

    # Le nom source (anglais), lui, reste intact -- c'est lui qui part vers ai-service.
    assert spain.name == "Spain"
    assert england.name == "England"


def test_loser_placeholder_resolved_one_level(client: TestClient, db_session: Session) -> None:
    """Un placeholder de type L résolu : « Perdant France-Espagne » / « Perdant FRA/ESP »."""
    france = Team(name="Zztest Loser France", fifa_code="ZLF")
    espagne = Team(name="Zztest Loser Espagne", fifa_code="ZLE")
    db_session.add_all([france, espagne])
    db_session.flush()

    semi = Match(
        num=90111,
        home_team_id=france.id,
        away_team_id=espagne.id,
        phase=MatchPhase.SEMI_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 14, 19, 0, tzinfo=timezone.utc),
    )
    third = Match(
        num=90211,
        home_placeholder="L90111",
        phase=MatchPhase.THIRD_PLACE,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 18, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([semi, third])
    db_session.commit()

    created = _match_from_response(client.get("/matches").json(), "third_place", third.id)
    assert created["home_placeholder_label"] == "Perdant Zztest Loser France-Zztest Loser Espagne"
    assert created["home_placeholder_label_short"] == "Perdant ZLF/ZLE"


def test_placeholder_label_falls_back_when_referenced_match_absent(
    client: TestClient, db_session: Session
) -> None:
    """Aucun match ne porte le num référencé → repli sur le libellé par numéro."""
    final = Match(
        num=90301,
        home_placeholder="W98765",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 19, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add(final)
    db_session.commit()

    created = _match_from_response(client.get("/matches").json(), "final", final.id)
    assert created["home_placeholder_label"] == "Vainqueur du match 98765"
    assert created["home_placeholder_label_short"] == "V. 98765"


def test_placeholder_label_falls_back_when_referenced_teams_unknown(
    client: TestClient, db_session: Session
) -> None:
    """Le match référencé existe mais ses équipes ne sont pas encore connues (chaîne de
    placeholders non résolue) → repli, pas de remontée d'un niveau."""
    unresolved_semi = Match(
        num=90401,
        home_placeholder="W90501",
        away_placeholder="W90502",
        phase=MatchPhase.SEMI_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 14, 19, 0, tzinfo=timezone.utc),
    )
    final = Match(
        num=90402,
        home_placeholder="W90401",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 19, 19, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([unresolved_semi, final])
    db_session.commit()

    created = _match_from_response(client.get("/matches").json(), "final", final.id)
    assert created["home_placeholder_label"] == "Vainqueur du match 90401"
    assert created["home_placeholder_label_short"] == "V. 90401"
