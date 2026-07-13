from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.ai_prediction import AiPrediction
from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.score import Score
from app.models.simulation_match_result import SimulationMatchResult
from app.models.simulation_run import SimulationRun
from app.models.team import Team
from app.models.user import User
from app.services import simulation
from app.services.ai_client import MatchPrediction

PAST_KICKOFF = datetime.now(timezone.utc) - timedelta(days=10)

# Préfixe Z : ne collisionne jamais avec les groupes réels du calendrier (A-L).
GROUP_NAMES = [f"Z{i}" for i in range(1, 13)]


# ---------------------------------------------------------------------------
# Fonctions pures : compute_group_standings, select_best_third_placed_teams,
# build_round_of_32_pairs. Aucune base de données.
# ---------------------------------------------------------------------------


def _standing(group: str, team_id: int, won: int, drawn: int, goals_for: int, goals_against: int) -> simulation.GroupStanding:
    return simulation.GroupStanding(
        group_name=group,
        team_id=team_id,
        played=won + drawn,
        won=won,
        drawn=drawn,
        lost=0,
        goals_for=goals_for,
        goals_against=goals_against,
    )


def test_compute_group_standings_orders_by_points_then_goal_difference() -> None:
    results = [
        simulation.GroupMatchResult(1, 2, 2, 0),
        simulation.GroupMatchResult(1, 3, 2, 0),
        simulation.GroupMatchResult(1, 4, 2, 0),
        simulation.GroupMatchResult(2, 3, 1, 0),
        simulation.GroupMatchResult(2, 4, 1, 1),
        simulation.GroupMatchResult(3, 4, 1, 0),
    ]

    standings = simulation.compute_group_standings("A", results)

    assert [s.team_id for s in standings] == [1, 2, 3, 4]
    assert (standings[0].points, standings[0].goal_diff) == (9, 6)
    assert (standings[1].points, standings[1].goal_diff) == (4, -1)
    assert (standings[2].points, standings[2].goal_diff) == (3, -2)
    assert (standings[3].points, standings[3].goal_diff) == (1, -3)


def test_select_best_third_placed_ranks_by_points_first() -> None:
    a = _standing("A", 1, won=2, drawn=0, goals_for=4, goals_against=1)  # 6 pts
    b = _standing("B", 2, won=1, drawn=1, goals_for=3, goals_against=2)  # 4 pts
    c = _standing("C", 3, won=0, drawn=1, goals_for=1, goals_against=3)  # 1 pt

    ranked = simulation.select_best_third_placed_teams([b, c, a], count=3)

    assert [s.team_id for s in ranked] == [1, 2, 3]


def test_select_best_third_placed_breaks_points_tie_with_goal_difference() -> None:
    a = _standing("A", 1, won=1, drawn=1, goals_for=4, goals_against=1)  # 4 pts, diff +3
    b = _standing("B", 2, won=1, drawn=1, goals_for=3, goals_against=2)  # 4 pts, diff +1

    ranked = simulation.select_best_third_placed_teams([b, a], count=2)

    assert [s.team_id for s in ranked] == [1, 2]


def test_select_best_third_placed_breaks_points_and_gd_tie_with_goals_scored() -> None:
    a = _standing("A", 1, won=1, drawn=1, goals_for=5, goals_against=2)  # 4 pts, diff +3
    b = _standing("B", 2, won=1, drawn=1, goals_for=4, goals_against=1)  # 4 pts, diff +3

    ranked = simulation.select_best_third_placed_teams([b, a], count=2)

    assert [s.team_id for s in ranked] == [1, 2]


def test_select_best_third_placed_total_tie_falls_back_deterministically_to_team_id() -> None:
    a = _standing("A", 5, won=1, drawn=1, goals_for=3, goals_against=1)
    b = _standing("B", 2, won=1, drawn=1, goals_for=3, goals_against=1)

    ranked = simulation.select_best_third_placed_teams([a, b], count=2)

    assert [s.team_id for s in ranked] == [2, 5]


def test_select_best_third_placed_returns_top_8_of_12() -> None:
    """La règle centrale du format 2026 : sur 12 groupes, seuls les 8 meilleurs 3es
    (tous groupes confondus) sont qualifiés."""
    thirds = [
        _standing(f"G{i}", i, won=(1 if i <= 8 else 0), drawn=0, goals_for=i, goals_against=0)
        for i in range(1, 13)
    ]

    ranked = simulation.select_best_third_placed_teams(thirds)

    assert len(ranked) == 8
    assert {s.team_id for s in ranked} == set(range(1, 9))


def test_build_round_of_32_pairs_never_pairs_same_group_and_uses_every_team_once() -> None:
    groups = GROUP_NAMES
    winners = [_standing(g, idx * 3 + 1, won=3, drawn=0, goals_for=5, goals_against=0) for idx, g in enumerate(groups)]
    runners_up = [
        _standing(g, idx * 3 + 2, won=2, drawn=0, goals_for=3, goals_against=1) for idx, g in enumerate(groups)
    ]
    thirds = [
        _standing(g, idx * 3 + 3, won=1, drawn=0, goals_for=2, goals_against=2) for idx, g in enumerate(groups)
    ]
    best_thirds = simulation.select_best_third_placed_teams(thirds, count=8)

    pairs = simulation.build_round_of_32_pairs(winners, runners_up, best_thirds)

    assert len(pairs) == 16
    all_ids = [team_id for pair in pairs for team_id in pair]
    assert len(all_ids) == len(set(all_ids)) == 32

    group_by_team_id = {s.team_id: s.group_name for s in winners + runners_up + thirds}
    for home_id, away_id in pairs:
        assert group_by_team_id[home_id] != group_by_team_id[away_id]


# ---------------------------------------------------------------------------
# Intégration base de données : run_realistic_simulation.
# ---------------------------------------------------------------------------


class _FakeAIClient:
    """Prédit un score déterministe et varié (jamais le vrai service IA). Journalise
    chaque appel pour permettre aux tests de vérifier ce qui a été réellement demandé."""

    def __init__(self) -> None:
        self.calls = 0
        self.predictions: dict[tuple[int, int], tuple[int, int]] = {}

    def predict_match(self, home_team_id: int, away_team_id: int, match_id: int | None = None) -> MatchPrediction:
        self.calls += 1
        home_score = (home_team_id * 3 + away_team_id) % 5
        away_score = (home_team_id + away_team_id * 2) % 5
        self.predictions[(home_team_id, away_team_id)] = (home_score, away_score)
        return MatchPrediction(predicted_home_score=home_score, predicted_away_score=away_score)


class _AlwaysUnavailableAIClient:
    def predict_match(self, home_team_id: int, away_team_id: int, match_id: int | None = None) -> None:
        return None


def _clear_real_matches(db_session: Session) -> None:
    """Le calendrier réel (48 équipes, 12 groupes A-L) contient déjà un tournoi complet :
    run_realistic_simulation le traiterait aussi, en plus du tournoi synthétique du test,
    faussant les décomptes. Purge le calendrier réel, sans effet hors de la transaction de
    test (même schéma que test_ai_predictions.py::_clear_matches)."""
    db_session.query(AiPrediction).delete()
    db_session.query(Match).delete()
    db_session.flush()


def _create_admin(db_session: Session, suffix: str = "") -> User:
    admin = User(
        email=f"simadmin{suffix}@example.com",
        username=f"simadmin{suffix}",
        hashed_password="x",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


def _build_full_tournament(
    db_session: Session, unplayed_pair: tuple[str, int] | None = None
) -> tuple[dict[str, list[Team]], dict[str, list[simulation.GroupMatchResult]]]:
    """Crée 12 groupes synthétiques de 4 équipes (préfixe Z), avec un résultat déterministe
    pour chacun des 6 matchs de chaque groupe -- format 2026 complet (48 équipes).

    Dans les 8 premiers groupes, le 3e de groupe termine avec 3 points (candidat plausible
    aux meilleurs 3es) ; dans les 4 derniers, avec seulement 1 point (jamais qualifiable) --
    sépare sans ambiguïté les 8 qualifiés des 4 recalés, pour un test reproductible.

    Tous les matchs sont déjà joués (gelés), sauf celui indiqué par `unplayed_pair`
    (nom du groupe, index du match dans le groupe 0-5) qui reste à venir.
    """
    teams_by_group: dict[str, list[Team]] = {}
    counter = 1
    for group in GROUP_NAMES:
        group_teams = []
        for i in range(4):
            team = Team(name=f"{group} T{i}", fifa_code=f"Z{counter:02d}", group_name=group)
            db_session.add(team)
            group_teams.append(team)
            counter += 1
        teams_by_group[group] = group_teams
    db_session.flush()

    group_results: dict[str, list[simulation.GroupMatchResult]] = {}

    for group_index, group in enumerate(GROUP_NAMES):
        t1, t2, t3, t4 = teams_by_group[group]
        if group_index < 8:
            # 3e de groupe (par le classement) termine à 3 points.
            fixtures = [
                (t1, t2, 2, 0),
                (t1, t3, 2, 0),
                (t1, t4, 2, 0),
                (t2, t3, 1, 0),
                (t2, t4, 1, 1),
                (t3, t4, 1, 0),
            ]
        else:
            # 3e de groupe termine à seulement 1 point : jamais parmi les 8 meilleurs.
            fixtures = [
                (t1, t2, 2, 0),
                (t1, t3, 3, 0),
                (t1, t4, 1, 0),
                (t2, t3, 2, 0),
                (t2, t4, 1, 0),
                (t3, t4, 0, 1),
            ]

        results = []
        for match_index, (home, away, home_score, away_score) in enumerate(fixtures):
            is_unplayed = unplayed_pair == (group, match_index)
            match = Match(
                home_team_id=home.id,
                away_team_id=away.id,
                phase=MatchPhase.GROUP,
                status=MatchStatus.SCHEDULED if is_unplayed else MatchStatus.FINISHED,
                kickoff_at=PAST_KICKOFF,
                home_score=None if is_unplayed else home_score,
                away_score=None if is_unplayed else away_score,
            )
            db_session.add(match)
            results.append(simulation.GroupMatchResult(home.id, away.id, home_score, away_score))
        group_results[group] = results

    db_session.flush()
    return teams_by_group, group_results


def test_run_realistic_simulation_freezes_already_played_matches(db_session: Session) -> None:
    """Test obligatoire : les matchs déjà joués gardent leur résultat réel, jamais
    resimulé."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "a")
    _teams_by_group, group_results = _build_full_tournament(db_session)
    fake = _FakeAIClient()

    run = simulation.run_realistic_simulation(db_session, created_by_user_id=admin.id, ai_client=fake)

    group_rows = (
        db_session.query(SimulationMatchResult)
        .filter(SimulationMatchResult.simulation_run_id == run.id, SimulationMatchResult.phase == MatchPhase.GROUP)
        .all()
    )
    assert len(group_rows) == 72
    assert all(row.is_frozen_real_result for row in group_rows)
    # L'IA n'est appelée que pour la phase finale (32 matchs) : aucun match de groupe à
    # simuler puisque les 72 sont déjà joués.
    assert fake.calls == 32

    real_scores = {
        (match_result.home_team_id, match_result.away_team_id): (match_result.home_score, match_result.away_score)
        for results in group_results.values()
        for match_result in results
    }
    for row in group_rows:
        assert (row.simulated_home_score, row.simulated_away_score) == real_scores[(row.home_team_id, row.away_team_id)]


def test_run_realistic_simulation_simulates_unplayed_match_via_ai(db_session: Session) -> None:
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "b")
    teams_by_group, _group_results = _build_full_tournament(db_session, unplayed_pair=("Z1", 0))
    t1, t2, _t3, _t4 = teams_by_group["Z1"]
    fake = _FakeAIClient()

    run = simulation.run_realistic_simulation(db_session, created_by_user_id=admin.id, ai_client=fake)

    row = (
        db_session.query(SimulationMatchResult)
        .filter(
            SimulationMatchResult.simulation_run_id == run.id,
            SimulationMatchResult.phase == MatchPhase.GROUP,
            SimulationMatchResult.home_team_id == t1.id,
            SimulationMatchResult.away_team_id == t2.id,
        )
        .one()
    )
    assert row.is_frozen_real_result is False
    expected_home, expected_away = fake.predictions[(t1.id, t2.id)]
    assert (row.simulated_home_score, row.simulated_away_score) == (expected_home, expected_away)


def test_run_realistic_simulation_isolation(db_session: Session) -> None:
    """Test obligatoire : aucune écriture vers matches/predictions/scores."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "c")
    _build_full_tournament(db_session)

    predictions_before = db_session.query(Prediction).count()
    scores_before = db_session.query(Score).count()
    matches_snapshot_before = {
        match.id: (match.home_score, match.away_score) for match in db_session.query(Match).all()
    }

    simulation.run_realistic_simulation(db_session, created_by_user_id=admin.id, ai_client=_FakeAIClient())

    assert db_session.query(Prediction).count() == predictions_before
    assert db_session.query(Score).count() == scores_before
    matches_snapshot_after = {
        match.id: (match.home_score, match.away_score) for match in db_session.query(Match).all()
    }
    assert matches_snapshot_after == matches_snapshot_before


def test_run_realistic_simulation_best_third_placed_rule_end_to_end(db_session: Session) -> None:
    """Test obligatoire : la règle des meilleurs 3es fonctionne, dans le pipeline complet
    groupes -> classements -> tableau -> finale."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "d")
    _teams_by_group, group_results = _build_full_tournament(db_session)

    # Oracle indépendant : mêmes données, calculées directement via les fonctions pures
    # déjà testées ci-dessus, pour vérifier que l'orchestration DB produit le même résultat.
    winners, runners_up, thirds = [], [], []
    for group_name, results in group_results.items():
        standings = simulation.compute_group_standings(group_name, results)
        winners.append(standings[0])
        runners_up.append(standings[1])
        thirds.append(standings[2])
    best_thirds = simulation.select_best_third_placed_teams(thirds)
    expected_qualifiers = (
        {s.team_id for s in winners} | {s.team_id for s in runners_up} | {s.team_id for s in best_thirds}
    )
    assert len(expected_qualifiers) == 32

    run = simulation.run_realistic_simulation(db_session, created_by_user_id=admin.id, ai_client=_FakeAIClient())

    all_results = (
        db_session.query(SimulationMatchResult).filter(SimulationMatchResult.simulation_run_id == run.id).all()
    )
    assert len(all_results) == 104

    r32_results = [r for r in all_results if r.phase == MatchPhase.ROUND_OF_32]
    assert len(r32_results) == 16
    actual_qualifiers = {r.home_team_id for r in r32_results} | {r.away_team_id for r in r32_results}
    assert actual_qualifiers == expected_qualifiers

    final_results = [r for r in all_results if r.phase == MatchPhase.FINAL]
    assert len(final_results) == 1
    assert final_results[0].winner_team_id is not None

    third_place_results = [r for r in all_results if r.phase == MatchPhase.THIRD_PLACE]
    assert len(third_place_results) == 1


def test_run_realistic_simulation_raises_and_persists_nothing_when_ai_unavailable(db_session: Session) -> None:
    """Test obligatoire : le dépassement/l'indisponibilité du service IA est géré
    proprement, sans donnée partielle."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "e")
    _build_full_tournament(db_session, unplayed_pair=("Z1", 0))

    runs_before = db_session.query(SimulationRun).count()
    results_before = db_session.query(SimulationMatchResult).count()

    with pytest.raises(simulation.AIServiceUnavailable):
        simulation.run_realistic_simulation(db_session, created_by_user_id=admin.id, ai_client=_AlwaysUnavailableAIClient())

    assert db_session.query(SimulationRun).count() == runs_before
    assert db_session.query(SimulationMatchResult).count() == results_before


def test_run_alternate_simulation_isolation(db_session: Session) -> None:
    """Étend le test d'isolation au mode alternatif : même en resimulant tout, aucune
    écriture vers matches/predictions/scores."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "altiso")
    _build_full_tournament(db_session)

    predictions_before = db_session.query(Prediction).count()
    scores_before = db_session.query(Score).count()
    matches_snapshot_before = {
        match.id: (match.home_score, match.away_score) for match in db_session.query(Match).all()
    }

    simulation.run_alternate_simulation(db_session, created_by_user_id=admin.id, ai_client=_FakeAIClient())

    assert db_session.query(Prediction).count() == predictions_before
    assert db_session.query(Score).count() == scores_before
    matches_snapshot_after = {
        match.id: (match.home_score, match.away_score) for match in db_session.query(Match).all()
    }
    assert matches_snapshot_after == matches_snapshot_before


def test_run_alternate_simulation_resimulates_already_played_matches(db_session: Session) -> None:
    """Le mode alternatif ne gèle jamais un résultat, contrairement au mode réaliste,
    même quand le match a déjà réellement été joué."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "altresim")
    _build_full_tournament(db_session)  # tout est déjà joué (aurait été gelé en mode réaliste)
    fake = _FakeAIClient()

    run = simulation.run_alternate_simulation(db_session, created_by_user_id=admin.id, ai_client=fake)

    group_rows = (
        db_session.query(SimulationMatchResult)
        .filter(SimulationMatchResult.simulation_run_id == run.id, SimulationMatchResult.phase == MatchPhase.GROUP)
        .all()
    )
    assert len(group_rows) == 72
    assert all(row.is_frozen_real_result is False for row in group_rows)
    # Tout est simulé, y compris les 72 matchs de groupe déjà joués (104 = 72 + 32 de phase finale).
    assert fake.calls == 104


def test_run_alternate_simulation_same_seed_gives_same_result(db_session: Session) -> None:
    """Test obligatoire : deux exécutions avec la même graine donnent le même résultat."""
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "altseed")
    _build_full_tournament(db_session)
    seed = "graine-de-test-fixe"

    run1 = simulation.run_alternate_simulation(
        db_session, created_by_user_id=admin.id, ai_client=_FakeAIClient(), seed=seed
    )
    run2 = simulation.run_alternate_simulation(
        db_session, created_by_user_id=admin.id, ai_client=_FakeAIClient(), seed=seed
    )

    assert run1.seed == run2.seed == seed

    def _signature(run_id: int) -> list[tuple]:
        rows = (
            db_session.query(SimulationMatchResult)
            .filter(SimulationMatchResult.simulation_run_id == run_id)
            .order_by(
                SimulationMatchResult.phase, SimulationMatchResult.home_team_id, SimulationMatchResult.away_team_id
            )
            .all()
        )
        return [
            (
                r.phase,
                r.home_team_id,
                r.away_team_id,
                r.simulated_home_score,
                r.simulated_away_score,
                r.winner_team_id,
            )
            for r in rows
        ]

    assert _signature(run1.id) == _signature(run2.id)


# ---------------------------------------------------------------------------
# Endpoints HTTP.
# ---------------------------------------------------------------------------


def test_post_simulations_requires_admin(client: TestClient, db_session: Session) -> None:
    non_admin = User(email="simreg@example.com", username="simreg", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.post("/simulations", json={"mode": "realiste"}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_post_simulations_alternate_mode_requires_admin(client: TestClient, db_session: Session) -> None:
    """Test obligatoire : le mode alternatif est lui aussi réservé aux administrateurs."""
    non_admin = User(email="simreg3@example.com", username="simreg3", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.post("/simulations", json={"mode": "alternatif"}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_get_simulations_requires_admin(client: TestClient, db_session: Session) -> None:
    non_admin = User(email="simreg2@example.com", username="simreg2", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.get("/simulations", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_get_simulation_404_for_unknown_id(client: TestClient, db_session: Session) -> None:
    admin = _create_admin(db_session, "f")
    token = create_access_token(subject=str(admin.id))

    response = client.get("/simulations/999999999", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404


def test_post_simulations_creates_full_tournament_for_admin(client: TestClient, db_session: Session) -> None:
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "g")
    _build_full_tournament(db_session)
    token = create_access_token(subject=str(admin.id))

    response = client.post(
        "/simulations",
        json={"mode": "realiste", "label": "Test réaliste"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["mode"] == "realiste"
    assert len(body["results"]) == 104
    run_id = body["id"]

    list_response = client.get("/simulations", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert any(item["id"] == run_id for item in list_response.json())

    detail_response = client.get(f"/simulations/{run_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_response.status_code == 200
    assert len(detail_response.json()["results"]) == 104


def test_post_simulations_alternate_mode_creates_full_tournament_for_admin(
    client: TestClient, db_session: Session
) -> None:
    _clear_real_matches(db_session)
    admin = _create_admin(db_session, "h")
    _build_full_tournament(db_session)
    token = create_access_token(subject=str(admin.id))

    response = client.post(
        "/simulations",
        json={"mode": "alternatif", "label": "Test alternatif"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["mode"] == "alternatif"
    assert len(body["results"]) == 104
    assert all(result["is_frozen_real_result"] is False for result in body["results"])
