import pandas as pd
import pytest

from app.services import elo
from app.services.data_prep import DEFAULT_FALLBACK_PATH, build_features, load_raw_matches

# Adresse injoignable (port 1, rien n'écoute) : échec de connexion immédiat, pour forcer
# un repli rapide et déterministe sur la copie locale, sans dépendre du réseau réel dans
# les tests.
UNREACHABLE_URL = "http://127.0.0.1:1"


def _match(
    date: str,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    tournament: str = "Friendly",
    neutral: bool = False,
) -> dict:
    return {
        "date": date,
        "home_team": home,
        "away_team": away,
        "home_score": home_score,
        "away_score": away_score,
        "tournament": tournament,
        "neutral": neutral,
    }


def _frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------------------------------------------------------------------
# Comportement des features, sur des scénarios synthétiques réduits.
# ---------------------------------------------------------------------------


def test_first_match_for_a_team_uses_initial_elo_and_zero_form() -> None:
    df = _frame([_match("2020-01-01", "TeamA", "TeamB", 1, 0)])
    features, _final_elo = build_features(df)

    row = features.iloc[0]
    assert row["elo_home_before"] == elo.INITIAL_ELO
    assert row["elo_away_before"] == elo.INITIAL_ELO
    assert row["elo_diff"] == 0.0
    assert row["home_form_goals_scored"] == 0
    assert row["home_avg_goals_scored"] == 0.0
    assert row["away_avg_goals_conceded"] == 0.0


def test_elo_and_form_update_after_a_match_and_carry_to_the_next() -> None:
    df = _frame(
        [
            _match("2020-01-01", "TeamA", "TeamB", 3, 0),
            _match("2020-02-01", "TeamA", "TeamC", 1, 1),
        ]
    )
    features, final_elo = build_features(df)

    first, second = features.iloc[0], features.iloc[1]
    assert first["elo_home_before"] == elo.INITIAL_ELO  # TeamA à son tout premier match

    expected_elo_after_first = elo.update_ratings(elo.INITIAL_ELO, elo.INITIAL_ELO, 3, 0, "Friendly")[0]
    assert second["elo_home_before"] == pytest.approx(expected_elo_after_first)
    assert second["home_form_goals_scored"] == 3
    assert second["home_form_goals_conceded"] == 0
    assert second["home_avg_goals_scored"] == 3.0

    team_a_final = final_elo.loc[final_elo["team"] == "TeamA", "elo"].item()
    assert team_a_final != elo.INITIAL_ELO


def test_recent_form_window_caps_at_ten_matches() -> None:
    """Le 11e match d'une équipe ne doit plus voir son tout premier dans sa forme récente."""
    rows = [_match(f"2020-01-{i + 1:02d}", "TeamA", "TeamB", 1, 0) for i in range(10)]
    rows.append(_match("2020-02-01", "TeamA", "TeamC", 0, 0))
    df = _frame(rows)

    features, _final_elo = build_features(df)

    last = features.iloc[-1]
    assert last["home_form_goals_scored"] == 10  # 10 x 1 but marqué, jamais 11
    # Buts encaissés au global (tous les matchs) : doit rester à 0 (aucun but encaissé).
    assert last["home_avg_goals_conceded"] == 0.0


def test_is_friendly_flag_reflects_tournament() -> None:
    df = _frame(
        [
            _match("2020-01-01", "TeamA", "TeamB", 1, 0, tournament="Friendly"),
            _match("2020-01-02", "TeamC", "TeamD", 1, 0, tournament="FIFA World Cup"),
        ]
    )
    features, _final_elo = build_features(df)

    assert bool(features.iloc[0]["is_friendly"]) is True
    assert bool(features.iloc[1]["is_friendly"]) is False


def test_same_date_matches_never_see_each_other() -> None:
    """Règle point-in-time : un match ne doit jamais dépendre d'un match de date
    postérieure OU ÉGALE -- y compris un autre match joué le même jour.

    TeamA joue deux matchs le même jour (scénario artificiel, impossible dans la vraie
    vie, mais qui isole précisément cette règle) : ni l'un ni l'autre ne doit voir le
    résultat de l'autre. Un match du lendemain, lui, doit voir les DEUX résultats de la
    veille appliqués.
    """
    df = _frame(
        [
            _match("2020-01-01", "TeamA", "TeamB", 5, 0),
            _match("2020-01-01", "TeamA", "TeamC", 3, 0),
            _match("2020-01-02", "TeamA", "TeamD", 0, 0),
        ]
    )
    features, _final_elo = build_features(df)

    same_day = features[features["date"] == pd.Timestamp("2020-01-01")]
    assert len(same_day) == 2
    # Les deux matchs du même jour partent de zéro pour TeamA : aucun des deux ne voit
    # le résultat de l'autre, même si l'un est "traité" avant l'autre dans le calcul.
    assert (same_day["elo_home_before"] == elo.INITIAL_ELO).all()
    assert (same_day["home_form_goals_scored"] == 0).all()

    next_day = features[features["date"] == pd.Timestamp("2020-01-02")].iloc[0]
    # Le lendemain, en revanche, voit bien les DEUX résultats de la veille combinés.
    assert next_day["elo_home_before"] != elo.INITIAL_ELO
    assert next_day["home_form_goals_scored"] == 5 + 3


# ---------------------------------------------------------------------------
# Test obligatoire : absence de fuite temporelle, sur le vrai dataset.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_raw_matches() -> pd.DataFrame:
    return load_raw_matches(source_url=UNREACHABLE_URL, fallback_path=DEFAULT_FALLBACK_PATH)


@pytest.fixture(scope="module")
def real_features(real_raw_matches: pd.DataFrame) -> pd.DataFrame:
    features, _final_elo = build_features(real_raw_matches)
    return features


def test_truncating_history_to_a_match_date_reproduces_identical_features(
    real_raw_matches: pd.DataFrame, real_features: pd.DataFrame
) -> None:
    """Test obligatoire (anti-fuite temporelle) : reprend un match au milieu du dataset,
    recalcule ses features en tronquant l'historique à SA date, et vérifie qu'elles sont
    identiques à celles calculées sur le dataset complet. Si une feature dépendait, même
    indirectement, d'un match de date postérieure ou égale, ce test échouerait."""
    target = real_features.iloc[len(real_features) // 2]
    target_date = target["date"]

    # Tronque à strictement avant la date cible, plus les matchs de la date cible elle-
    # même (nécessaires pour recalculer le match cible, mais qui ne doivent pas se voir
    # entre eux -- déjà couvert par test_same_date_matches_never_see_each_other).
    truncated_raw = real_raw_matches[real_raw_matches["date"] <= target_date]
    assert len(truncated_raw) < len(real_raw_matches)  # le dataset est bien tronqué

    truncated_features, _ = build_features(truncated_raw)

    recomputed = truncated_features[
        (truncated_features["date"] == target_date)
        & (truncated_features["home_team"] == target["home_team"])
        & (truncated_features["away_team"] == target["away_team"])
    ]
    assert len(recomputed) == 1
    recomputed = recomputed.iloc[0]

    feature_columns = [
        "elo_home_before",
        "elo_away_before",
        "elo_diff",
        "home_form_goals_scored",
        "home_form_goals_conceded",
        "away_form_goals_scored",
        "away_form_goals_conceded",
        "home_avg_goals_scored",
        "home_avg_goals_conceded",
        "away_avg_goals_scored",
        "away_avg_goals_conceded",
        "is_friendly",
        "neutral",
    ]
    for column in feature_columns:
        assert recomputed[column] == pytest.approx(target[column]), f"fuite temporelle détectée sur {column}"


def test_no_feature_ever_uses_a_same_or_later_match_across_the_real_dataset(
    real_raw_matches: pd.DataFrame, real_features: pd.DataFrame
) -> None:
    """Renforce le test précédent à grande échelle : pour un échantillon de matchs
    espacés dans tout le dataset (pas seulement celui du milieu), la troncature à leur
    propre date doit toujours reproduire exactement les mêmes features. Échantillon
    volontairement réduit (chaque itération refait un build_features complet) : de quoi
    couvrir plusieurs époques du dataset sans ralentir excessivement la suite de tests.
    """
    sample = real_features.iloc[:: max(1, len(real_features) // 6)]

    for _, target in sample.iterrows():
        truncated_raw = real_raw_matches[real_raw_matches["date"] <= target["date"]]
        truncated_features, _ = build_features(truncated_raw)

        recomputed = truncated_features[
            (truncated_features["date"] == target["date"])
            & (truncated_features["home_team"] == target["home_team"])
            & (truncated_features["away_team"] == target["away_team"])
        ].iloc[0]

        assert recomputed["elo_home_before"] == pytest.approx(target["elo_home_before"])
        assert recomputed["elo_away_before"] == pytest.approx(target["elo_away_before"])
        assert recomputed["home_form_goals_scored"] == target["home_form_goals_scored"]
        assert recomputed["away_form_goals_scored"] == target["away_form_goals_scored"]
