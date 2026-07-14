import math

import numpy as np
import pandas as pd
import pytest

from app.services import evaluation as ev
from app.services.elo import INITIAL_ELO, update_ratings


# ---------------------------------------------------------------------------
# outcome_label() et temporal_split() : brique de base, anti-fuite temporelle.
# ---------------------------------------------------------------------------


def test_outcome_label() -> None:
    assert ev.outcome_label(2, 1) == "home_win"
    assert ev.outcome_label(1, 2) == "away_win"
    assert ev.outcome_label(1, 1) == "draw"


def _dated_df(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "home_team": ["A"] * len(dates),
            "away_team": ["B"] * len(dates),
            "home_score": [1] * len(dates),
            "away_score": [0] * len(dates),
            "elo_home_before": [1500.0] * len(dates),
            "elo_away_before": [1500.0] * len(dates),
        }
    )


def test_temporal_split_respects_cutoff_and_has_no_overlap() -> None:
    """Test obligatoire : PAS de fuite temporelle -- le train ne doit contenir aucun
    match de date postérieure ou égale à la coupure, le test aucun match antérieur."""
    df = _dated_df(["2020-01-01", "2021-06-15", "2023-12-31", "2024-01-01", "2025-01-01"])
    train, test = ev.temporal_split(df, pd.Timestamp("2024-01-01"))

    assert len(train) == 3
    assert len(test) == 2
    assert (train["date"] < pd.Timestamp("2024-01-01")).all()
    assert (test["date"] >= pd.Timestamp("2024-01-01")).all()
    assert train["date"].max() < test["date"].min()


def test_temporal_split_is_not_a_random_shuffle() -> None:
    """Le découpage doit rester déterministe et chronologique, pas un échantillonnage
    aléatoire -- rejouer le split doit produire exactement le même résultat."""
    df = _dated_df(["2022-03-01", "2023-07-01", "2024-05-01", "2024-09-01"])
    train1, test1 = ev.temporal_split(df, pd.Timestamp("2024-01-01"))
    train2, test2 = ev.temporal_split(df, pd.Timestamp("2024-01-01"))
    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(test1, test2)


# ---------------------------------------------------------------------------
# Métriques : valeurs calculées à la main sur de petits cas connus.
# ---------------------------------------------------------------------------


def _predictions(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_log_loss_matches_hand_computed_value() -> None:
    predictions = _predictions(
        [
            {"p_home_win": 0.5, "p_draw": 0.3, "p_away_win": 0.2, "actual_outcome": "home_win"},
            {"p_home_win": 0.2, "p_draw": 0.3, "p_away_win": 0.5, "actual_outcome": "away_win"},
        ]
    )
    expected = -(math.log(0.5) + math.log(0.5)) / 2
    assert ev.log_loss(predictions) == pytest.approx(expected)


def test_log_loss_is_near_zero_for_confident_correct_predictions() -> None:
    predictions = _predictions(
        [{"p_home_win": 0.999, "p_draw": 0.0005, "p_away_win": 0.0005, "actual_outcome": "home_win"}]
    )
    assert ev.log_loss(predictions) == pytest.approx(-math.log(0.999), abs=1e-6)


def test_log_loss_does_not_blow_up_on_zero_probability() -> None:
    """Une probabilité nulle sur l'issue réelle ne doit pas produire -inf/NaN (écrêtage)."""
    predictions = _predictions(
        [{"p_home_win": 0.0, "p_draw": 0.0, "p_away_win": 1.0, "actual_outcome": "home_win"}]
    )
    loss = ev.log_loss(predictions)
    assert math.isfinite(loss)
    assert loss > 0


def test_brier_score_matches_hand_computed_value() -> None:
    predictions = _predictions(
        [{"p_home_win": 0.7, "p_draw": 0.2, "p_away_win": 0.1, "actual_outcome": "home_win"}]
    )
    expected = (0.7 - 1) ** 2 + (0.2 - 0) ** 2 + (0.1 - 0) ** 2
    assert ev.brier_score(predictions) == pytest.approx(expected)


def test_brier_score_is_zero_for_perfect_confident_predictions() -> None:
    predictions = _predictions(
        [
            {"p_home_win": 1.0, "p_draw": 0.0, "p_away_win": 0.0, "actual_outcome": "home_win"},
            {"p_home_win": 0.0, "p_draw": 0.0, "p_away_win": 1.0, "actual_outcome": "away_win"},
        ]
    )
    assert ev.brier_score(predictions) == pytest.approx(0.0)


def test_outcome_accuracy_hand_computed() -> None:
    predictions = _predictions(
        [
            {"p_home_win": 0.6, "p_draw": 0.3, "p_away_win": 0.1, "actual_outcome": "home_win"},  # correct
            {"p_home_win": 0.6, "p_draw": 0.3, "p_away_win": 0.1, "actual_outcome": "draw"},  # faux
            {"p_home_win": 0.1, "p_draw": 0.2, "p_away_win": 0.7, "actual_outcome": "away_win"},  # correct
        ]
    )
    assert ev.outcome_accuracy(predictions) == pytest.approx(2 / 3)


def test_exact_score_accuracy_hand_computed() -> None:
    predictions = _predictions(
        [
            {"pred_home_goals": 2, "pred_away_goals": 1, "actual_home_score": 2, "actual_away_score": 1},
            {"pred_home_goals": 1, "pred_away_goals": 0, "actual_home_score": 2, "actual_away_score": 0},
        ]
    )
    assert ev.exact_score_accuracy(predictions) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Calibration.
# ---------------------------------------------------------------------------


def test_calibration_curve_bins_cover_every_pooled_observation() -> None:
    predictions = _predictions(
        [
            {"p_home_win": 0.9, "p_draw": 0.05, "p_away_win": 0.05, "actual_outcome": "home_win"},
            {"p_home_win": 0.1, "p_draw": 0.1, "p_away_win": 0.8, "actual_outcome": "away_win"},
        ]
    )
    curve = ev.calibration_curve(predictions, n_bins=10)
    assert curve["count"].sum() == 2 * 3  # 3 flux de probabilités par match


def test_calibration_curve_is_accurate_on_a_deliberately_well_calibrated_dataset() -> None:
    """Construit un jeu où, pour p=0.7, exactement 70% des observations sont positives --
    la tranche correspondante doit retrouver cette fréquence exactement."""
    rows = []
    for is_home_win in [True] * 7 + [False] * 3:
        rows.append(
            {
                "p_home_win": 0.7,
                "p_draw": 0.15,
                "p_away_win": 0.15,
                "actual_outcome": "home_win" if is_home_win else "draw",
            }
        )
    predictions = _predictions(rows)
    curve = ev.calibration_curve(predictions, n_bins=10)

    home_win_bin = curve[(curve["bin_low"] <= 0.7) & (curve["bin_high"] > 0.7)].iloc[0]
    assert home_win_bin["predicted_mean"] == pytest.approx(0.7)
    assert home_win_bin["observed_frequency"] == pytest.approx(0.7)


def test_calibration_curve_includes_probability_of_exactly_one() -> None:
    predictions = _predictions(
        [{"p_home_win": 1.0, "p_draw": 0.0, "p_away_win": 0.0, "actual_outcome": "home_win"}]
    )
    curve = ev.calibration_curve(predictions, n_bins=10)
    last_bin = curve[curve["bin_high"] == 1.0].iloc[0]
    assert last_bin["count"] >= 1


# ---------------------------------------------------------------------------
# Références : hasard et favori Elo.
# ---------------------------------------------------------------------------


def test_random_baseline_accuracy_is_exactly_one_third_not_argmax_biased() -> None:
    """Piège explicite : si l'exactitude du hasard était recalculée par argmax sur des
    probabilités égales, elle refléterait la fréquence de home_win du jeu de test (biais)
    plutôt que 1/3 -- vérifie que ce n'est PAS le cas."""
    predictions = _predictions(
        [{"p_home_win": 0.8, "p_draw": 0.1, "p_away_win": 0.1, "actual_outcome": "home_win"}] * 10
    )
    metrics = ev.random_baseline_metrics(predictions)
    assert metrics["outcome_accuracy"] == pytest.approx(1 / 3)


def test_random_baseline_log_loss_equals_log_of_three() -> None:
    predictions = _predictions(
        [{"p_home_win": 0.8, "p_draw": 0.1, "p_away_win": 0.1, "actual_outcome": "home_win"}]
    )
    metrics = ev.random_baseline_metrics(predictions)
    assert metrics["log_loss"] == pytest.approx(math.log(3))


def test_elo_favorite_baseline_predicts_higher_elo_team_wins() -> None:
    test_df = pd.DataFrame(
        {
            "elo_home_before": [1600.0, 1400.0],
            "elo_away_before": [1400.0, 1600.0],
            "home_score": [2, 0],
            "away_score": [1, 2],
        }
    )
    metrics = ev.elo_favorite_baseline_metrics(test_df)
    assert metrics["outcome_accuracy"] == pytest.approx(1.0)


def test_elo_favorite_baseline_never_predicts_a_draw() -> None:
    """Une équipe favorite qui fait match nul doit être comptée comme une erreur du
    favori Elo (celui-ci ne prédit jamais de nul, par construction)."""
    test_df = pd.DataFrame(
        {"elo_home_before": [1600.0], "elo_away_before": [1400.0], "home_score": [1], "away_score": [1]}
    )
    metrics = ev.elo_favorite_baseline_metrics(test_df)
    assert metrics["outcome_accuracy"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# evaluate() de bout en bout : sur un mini-championnat synthétique où une équipe
# domine systématiquement, le modèle ajusté doit nettement battre les deux références.
# ---------------------------------------------------------------------------


def _synthetic_league_with_split() -> pd.DataFrame:
    """Giants bat systématiquement Minnows, sur plusieurs saisons de part et d'autre
    de la coupure -- un modèle correctement ajusté doit generaliser cette régularité
    au test set, un hasard ou un mauvais modèle non.

    L'Elo "avant match" est recalculé itérativement (comme le ferait data_prep.py),
    pas fixé par identité d'équipe : sinon la référence favori-Elo serait artificiellement
    parfaite dès le premier match, faussant la comparaison avec le modèle Dixon-Coles."""
    fixtures = [("Giants", "Minnows", 4, 0), ("Minnows", "Giants", 0, 3)]
    elo = {"Giants": INITIAL_ELO, "Minnows": INITIAL_ELO}
    rows = []
    for season in range(10):
        for i, (home, away, hs, a_) in enumerate(fixtures):
            rows.append(
                {
                    "date": pd.Timestamp("2015-01-01") + pd.Timedelta(days=30 * (season * len(fixtures) + i)),
                    "home_team": home,
                    "away_team": away,
                    "home_score": hs,
                    "away_score": a_,
                    "tournament": "Friendly",
                    "elo_home_before": elo[home],
                    "elo_away_before": elo[away],
                }
            )
            elo[home], elo[away] = update_ratings(elo[home], elo[away], hs, a_, "Friendly")
    return pd.DataFrame(rows)


def test_evaluate_end_to_end_beats_both_baselines_on_a_lopsided_synthetic_league() -> None:
    df = _synthetic_league_with_split()
    # Seasons 0-6 (14 matchs) à l'entraînement, saisons 7-9 (6 matchs) au test -- l'écart
    # d'Elo entre Giants et Minnows n'est pas encore extrême aux premiers matchs, donc le
    # favori Elo n'est pas artificiellement parfait : comparaison honnête avec Dixon-Coles.
    split_date = pd.Timestamp("2016-03-01")
    assert (df["date"] < split_date).sum() > 0
    assert (df["date"] >= split_date).sum() > 0

    result = ev.evaluate(df, split_date=split_date)

    assert result.model_metrics["log_loss"] < result.random_metrics["log_loss"]
    assert result.model_metrics["outcome_accuracy"] > result.random_metrics["outcome_accuracy"]
    assert result.model_metrics["outcome_accuracy"] >= result.elo_metrics["outcome_accuracy"]


def test_evaluate_raises_when_split_leaves_an_empty_side() -> None:
    df = _synthetic_league_with_split()
    with pytest.raises(ValueError):
        ev.evaluate(df, split_date=pd.Timestamp("1900-01-01"))  # tout dans le test, rien à l'entraînement
