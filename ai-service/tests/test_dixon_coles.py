import numpy as np
import pandas as pd
import pytest

from app.services import dixon_coles as dc


def _model(
    attack: dict[str, float], defense: dict[str, float], home_advantage: float = 0.0, rho: float = 0.0
) -> dc.DixonColesModel:
    return dc.DixonColesModel(
        attack=attack,
        defense=defense,
        home_advantage=home_advantage,
        rho=rho,
        reference_team=next(iter(attack)),
        fitted_matches=0,
    )


# ---------------------------------------------------------------------------
# tau() et score_matrix() : mathématiques pures, aucun ajustement.
# ---------------------------------------------------------------------------


def test_tau_is_neutral_outside_low_scores() -> None:
    assert dc.tau(2, 2, 1.3, 1.1, rho=0.1) == 1.0
    assert dc.tau(3, 0, 1.3, 1.1, rho=0.1) == 1.0
    assert dc.tau(0, 3, 1.3, 1.1, rho=0.1) == 1.0


def test_tau_corrects_the_four_low_scores_when_rho_nonzero() -> None:
    rho = 0.1
    assert dc.tau(0, 0, 1.3, 1.1, rho) != 1.0
    assert dc.tau(0, 1, 1.3, 1.1, rho) != 1.0
    assert dc.tau(1, 0, 1.3, 1.1, rho) != 1.0
    assert dc.tau(1, 1, 1.3, 1.1, rho) != 1.0


def test_tau_is_identity_when_rho_is_zero() -> None:
    """rho=0 doit ramener exactement au Poisson non corrélé (aucune corrélation)."""
    for x, y in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        assert dc.tau(x, y, 1.3, 1.1, rho=0.0) == 1.0


def test_score_matrix_sums_to_one() -> None:
    """Test obligatoire : les probabilités somment à 1."""
    matrix = dc.score_matrix(lambda_home=1.6, lambda_away=1.1, rho=0.08)
    assert matrix.sum() == pytest.approx(1.0)
    assert (matrix >= 0).all()


def test_score_matrix_sums_to_one_for_various_rates_and_rho() -> None:
    for lambda_home, lambda_away, rho in [(0.3, 0.2, 0.0), (2.5, 2.5, 0.15), (0.9, 3.4, -0.1)]:
        matrix = dc.score_matrix(lambda_home, lambda_away, rho)
        assert matrix.sum() == pytest.approx(1.0)
        assert (matrix >= 0).all()


def test_score_matrix_shape_matches_max_goals() -> None:
    matrix = dc.score_matrix(1.5, 1.2, rho=0.05, max_goals=6)
    assert matrix.shape == (7, 7)


# ---------------------------------------------------------------------------
# Cohérence de la matrice des scores et des probabilités dérivées.
# ---------------------------------------------------------------------------


def test_outcome_probabilities_partition_the_matrix_exactly() -> None:
    """Test obligatoire : la matrice des scores est cohérente -- victoire/nul/défaite
    partitionnent exactement la matrice (aucune case comptée deux fois, aucune oubliée)."""
    matrix = dc.score_matrix(lambda_home=1.7, lambda_away=1.0, rho=0.1)
    home_win, draw, away_win = dc.match_outcome_probabilities(matrix)

    assert home_win + draw + away_win == pytest.approx(matrix.sum())
    assert home_win + draw + away_win == pytest.approx(1.0)

    # Repli naïf (double boucle), pour vérifier indépendamment le découpage tril/triu/trace.
    naive_home_win = sum(
        matrix[i, j] for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i > j
    )
    naive_draw = sum(matrix[i, i] for i in range(matrix.shape[0]))
    naive_away_win = sum(
        matrix[i, j] for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i < j
    )
    assert home_win == pytest.approx(naive_home_win)
    assert draw == pytest.approx(naive_draw)
    assert away_win == pytest.approx(naive_away_win)


def test_most_likely_score_matches_the_actual_maximum_cell() -> None:
    matrix = dc.score_matrix(lambda_home=1.4, lambda_away=1.1, rho=0.1)
    home_goals, away_goals = dc.most_likely_score(matrix)

    assert matrix[home_goals, away_goals] == pytest.approx(matrix.max())


def test_most_likely_score_on_a_hand_built_matrix() -> None:
    matrix = np.zeros((3, 3))
    matrix[2, 1] = 0.9
    matrix[0, 0] = 0.1
    assert dc.most_likely_score(matrix) == (2, 1)


def test_higher_lambda_home_shifts_probability_toward_home_win() -> None:
    weak_home = dc.score_matrix(lambda_home=0.6, lambda_away=1.8, rho=0.0)
    strong_home = dc.score_matrix(lambda_home=2.4, lambda_away=1.8, rho=0.0)

    weak_home_win, _, _ = dc.match_outcome_probabilities(weak_home)
    strong_home_win, _, _ = dc.match_outcome_probabilities(strong_home)
    assert strong_home_win > weak_home_win


# ---------------------------------------------------------------------------
# DixonColesModel : prédiction à partir de forces connues.
# ---------------------------------------------------------------------------


def test_a_much_stronger_team_has_a_higher_win_probability() -> None:
    """Test obligatoire : une équipe nettement plus forte a une probabilité de victoire
    supérieure -- dans les deux sens (à domicile et à l'extérieur)."""
    model = _model(
        attack={"Strong": 1.2, "Weak": -1.2},
        defense={"Strong": -1.0, "Weak": 1.0},
        home_advantage=0.0,
    )

    home_win, _draw, away_win = dc.match_outcome_probabilities(model.score_matrix("Strong", "Weak"))
    assert home_win > away_win

    home_win2, _draw2, away_win2 = dc.match_outcome_probabilities(model.score_matrix("Weak", "Strong"))
    assert away_win2 > home_win2


def test_home_advantage_increases_home_win_probability_between_equal_teams() -> None:
    equal_attack_defense = {"A": 0.0, "B": 0.0}
    neutral_model = _model(equal_attack_defense, equal_attack_defense, home_advantage=0.0)
    home_favored_model = _model(equal_attack_defense, equal_attack_defense, home_advantage=0.3)

    neutral_home_win, _, _ = dc.match_outcome_probabilities(neutral_model.score_matrix("A", "B"))
    favored_home_win, _, _ = dc.match_outcome_probabilities(home_favored_model.score_matrix("A", "B"))
    assert favored_home_win > neutral_home_win


def test_unknown_team_falls_back_to_average_strength_instead_of_crashing() -> None:
    model = _model(attack={"Known": 0.5}, defense={"Known": -0.5})
    lambda_home, lambda_away = model.rates("Known", "NeverSeenBefore")
    assert lambda_home > 0
    assert lambda_away > 0


# ---------------------------------------------------------------------------
# fit() : maximum de vraisemblance sur un mini-championnat synthétique.
# ---------------------------------------------------------------------------


def _synthetic_league() -> pd.DataFrame:
    """Mini-championnat à 4 équipes, où "Giants" écrase systématiquement tout le monde
    et "Minnows" perd systématiquement -- suffisamment marqué pour qu'un ajustement
    correct retrouve un ordre de force sans ambiguïté."""
    rows = []
    results = [
        ("Giants", "Rovers", 4, 0),
        ("Rovers", "Giants", 0, 3),
        ("Giants", "United", 3, 1),
        ("United", "Giants", 1, 4),
        ("Giants", "Minnows", 5, 0),
        ("Minnows", "Giants", 0, 4),
        ("Rovers", "United", 1, 1),
        ("United", "Rovers", 2, 2),
        ("Rovers", "Minnows", 2, 0),
        ("Minnows", "Rovers", 0, 2),
        ("United", "Minnows", 3, 0),
        ("Minnows", "United", 0, 3),
    ]
    for i, (home, away, hs, as_) in enumerate(results):
        # Répété sur plusieurs "saisons" : plus de matchs, ajustement mieux contraint.
        for season in range(6):
            rows.append(
                {
                    "date": pd.Timestamp("2010-01-01") + pd.Timedelta(days=30 * (season * len(results) + i)),
                    "home_team": home,
                    "away_team": away,
                    "home_score": hs,
                    "away_score": as_,
                    "tournament": "Friendly",
                }
            )
    return pd.DataFrame(rows)


def test_fit_recovers_the_correct_strength_ordering() -> None:
    df = _synthetic_league()
    model = dc.fit(df)

    # Force nette = attaque - défense (une bonne équipe attaque bien ET défend bien,
    # donc une défense faible -- au sens du paramètre, négative).
    strength = {team: model.attack[team] - model.defense[team] for team in model.attack}
    assert strength["Giants"] > strength["Rovers"]
    assert strength["Giants"] > strength["United"]
    assert strength["Rovers"] > strength["Minnows"]
    assert strength["United"] > strength["Minnows"]


def test_fit_respects_point_in_time_cutoff() -> None:
    """Le modèle ajusté avec une coupure ne doit JAMAIS refléter des matchs postérieurs
    ou égaux à cette coupure -- sinon la contrainte point-in-time serait violée."""
    df = _synthetic_league()

    # Injecte une razzia tardive et écrasante de "Rovers", après une coupure nette.
    cutoff = pd.Timestamp("2030-01-01")
    late_rows = [
        {
            "date": cutoff + pd.Timedelta(days=10 * i),
            "home_team": "Rovers",
            "away_team": "Minnows",
            "home_score": 9,
            "away_score": 0,
            "tournament": "Friendly",
        }
        for i in range(20)
    ]
    df_with_late_surge = pd.concat([df, pd.DataFrame(late_rows)], ignore_index=True)

    model_before_surge = dc.fit(df_with_late_surge, as_of_date=cutoff)
    model_with_full_history = dc.fit(df_with_late_surge, as_of_date=None)

    assert model_before_surge.fitted_matches < model_with_full_history.fitted_matches
    # La razzia tardive ne doit avoir influencé QUE le modèle qui l'a vue.
    assert model_with_full_history.attack["Rovers"] > model_before_surge.attack["Rovers"]


def test_save_and_load_model_round_trip(tmp_path) -> None:
    df = _synthetic_league()
    model = dc.fit(df)

    ratings_path = tmp_path / "ratings.parquet"
    params_path = tmp_path / "params.json"
    dc.save_model(model, ratings_path=ratings_path, params_path=params_path)
    reloaded = dc.load_model(ratings_path=ratings_path, params_path=params_path)

    assert reloaded.home_advantage == pytest.approx(model.home_advantage)
    assert reloaded.rho == pytest.approx(model.rho)
    for team in model.attack:
        assert reloaded.attack[team] == pytest.approx(model.attack[team])
        assert reloaded.defense[team] == pytest.approx(model.defense[team])
