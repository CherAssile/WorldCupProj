"""Prépare le dataset d'entraînement du futur modèle de prédiction : note Elo, forme
récente, moyennes de buts, avantage du terrain et enjeu du match, pour chaque match.

Contrainte point-in-time (règle d'or, CLAUDE.md) : la feature d'un match ne doit JAMAIS
dépendre d'un match de date postérieure OU ÉGALE -- y compris un autre match joué le même
jour. C'est la source d'erreur numéro un de ce type de projet (fuite temporelle) : voir
tests/test_data_prep.py pour la vérification dédiée.

Source : dataset public "International football results" (mirror GitHub du dataset
Kaggle du même nom -- même source que backend/app/services/historical_seed.py, qui
l'utilise déjà pour historical_matches, filtrée là à la seule Coupe du monde). Repli sur
une copie locale si le téléchargement échoue.

Usage : python -m app.services.data_prep
"""
from __future__ import annotations

import io
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pandas as pd

from app.services.elo import INITIAL_ELO, update_ratings

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_FALLBACK_PATH = DATA_DIR / "international_results_fallback.csv"
DEFAULT_OUTPUT_DATASET_PATH = DATA_DIR / "prepared_matches.parquet"
DEFAULT_OUTPUT_ELO_PATH = DATA_DIR / "elo_ratings_final.parquet"

# Nombre de matchs pris en compte pour la forme récente (buts marqués/encaissés).
FORM_WINDOW = 10

FEATURE_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "neutral",
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
]


def load_raw_matches(
    source_url: str = DEFAULT_SOURCE_URL,
    fallback_path: Path = DEFAULT_FALLBACK_PATH,
    timeout: float = 20.0,
) -> pd.DataFrame:
    """Télécharge le dataset source ; repli sur la copie locale si indisponible.

    Exclut les matchs pas encore joués (calendrier futur, ex. les demies du Mondial 2026
    dans ce dataset) : aucun résultat à apprendre, ils n'ont pas leur place dans un
    dataset d'entraînement.
    """
    try:
        response = httpx.get(source_url, timeout=timeout)
        response.raise_for_status()
        text = response.text
    except httpx.HTTPError as exc:
        logger.warning("Téléchargement du dataset impossible (%s), repli sur %s.", exc, fallback_path)
        text = fallback_path.read_text(encoding="utf-8")

    # pandas traite "NA" comme valeur manquante par défaut (déjà le cas pour les scores
    # et équipes des matchs futurs de ce dataset) : dropna suffit, pas de parsing manuel.
    df = pd.read_csv(io.StringIO(text))
    df = df.dropna(subset=["home_team", "away_team", "home_score", "away_score"]).copy()

    df["date"] = pd.to_datetime(df["date"])
    df["neutral"] = df["neutral"].astype(str).str.upper() == "TRUE"
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)

    return df.reset_index(drop=True)


@dataclass
class _TeamState:
    """État courant d'une équipe, juste avant son prochain match."""

    elo: float = INITIAL_ELO
    recent_goals_scored: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    recent_goals_conceded: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    total_goals_scored: int = 0
    total_goals_conceded: int = 0
    matches_played: int = 0

    def snapshot(self) -> dict[str, float]:
        """Features calculées à partir de l'état actuel, AVANT tout match à venir."""
        return {
            "elo": self.elo,
            "form_goals_scored": sum(self.recent_goals_scored),
            "form_goals_conceded": sum(self.recent_goals_conceded),
            "avg_goals_scored": (self.total_goals_scored / self.matches_played) if self.matches_played else 0.0,
            "avg_goals_conceded": (self.total_goals_conceded / self.matches_played) if self.matches_played else 0.0,
        }

    def record_match(self, goals_scored: int, goals_conceded: int) -> None:
        self.recent_goals_scored.append(goals_scored)
        self.recent_goals_conceded.append(goals_conceded)
        self.total_goals_scored += goals_scored
        self.total_goals_conceded += goals_conceded
        self.matches_played += 1


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcule les features de chaque match, un jour à la fois, dans l'ordre
    chronologique. Renvoie (dataset préparé, notes Elo finales par équipe).

    Traite chaque date comme un lot indivisible : toutes les features des matchs d'une
    même date sont calculées à partir de l'état figé à la fin de la date précédente,
    AVANT qu'aucune mise à jour de cette date ne soit appliquée. Deux matchs du même jour
    sont ainsi mutuellement invisibles -- seuls les matchs de date strictement antérieure
    influencent une feature. Les mises à jour (Elo, historique) ne sont appliquées qu'une
    fois toutes les features de la date déjà calculées.
    """
    states: dict[str, _TeamState] = defaultdict(_TeamState)
    rows: list[dict] = []

    for _, day_matches in df.groupby("date", sort=True):
        for _, match in day_matches.iterrows():
            home = states[match["home_team"]]
            away = states[match["away_team"]]
            home_snap = home.snapshot()
            away_snap = away.snapshot()

            rows.append(
                {
                    "date": match["date"],
                    "home_team": match["home_team"],
                    "away_team": match["away_team"],
                    "home_score": match["home_score"],
                    "away_score": match["away_score"],
                    "tournament": match["tournament"],
                    "neutral": bool(match["neutral"]),
                    "elo_home_before": home_snap["elo"],
                    "elo_away_before": away_snap["elo"],
                    "elo_diff": home_snap["elo"] - away_snap["elo"],
                    "home_form_goals_scored": home_snap["form_goals_scored"],
                    "home_form_goals_conceded": home_snap["form_goals_conceded"],
                    "away_form_goals_scored": away_snap["form_goals_scored"],
                    "away_form_goals_conceded": away_snap["form_goals_conceded"],
                    "home_avg_goals_scored": home_snap["avg_goals_scored"],
                    "home_avg_goals_conceded": home_snap["avg_goals_conceded"],
                    "away_avg_goals_scored": away_snap["avg_goals_scored"],
                    "away_avg_goals_conceded": away_snap["avg_goals_conceded"],
                    "is_friendly": match["tournament"] == "Friendly",
                }
            )

        # Mises à jour appliquées seulement maintenant : invisibles aux matchs déjà
        # traités ci-dessus (même date), visibles seulement à partir du jour suivant.
        for _, match in day_matches.iterrows():
            home = states[match["home_team"]]
            away = states[match["away_team"]]
            new_home_elo, new_away_elo = update_ratings(
                home.elo, away.elo, match["home_score"], match["away_score"], match["tournament"]
            )
            home.elo = new_home_elo
            away.elo = new_away_elo
            home.record_match(match["home_score"], match["away_score"])
            away.record_match(match["away_score"], match["home_score"])

    features = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    final_elo = (
        pd.DataFrame({"team": team, "elo": state.elo} for team, state in states.items())
        .sort_values("team")
        .reset_index(drop=True)
    )
    return features, final_elo


@dataclass
class PrepareResult:
    matches_prepared: int
    teams_rated: int
    output_dataset_path: Path
    output_elo_path: Path


def prepare_dataset(
    source_url: str = DEFAULT_SOURCE_URL,
    fallback_path: Path = DEFAULT_FALLBACK_PATH,
    output_dataset_path: Path = DEFAULT_OUTPUT_DATASET_PATH,
    output_elo_path: Path = DEFAULT_OUTPUT_ELO_PATH,
) -> PrepareResult:
    """Pipeline complet : charge, calcule les features, sauvegarde en parquet."""
    raw = load_raw_matches(source_url, fallback_path)
    features, final_elo = build_features(raw)

    output_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_dataset_path, index=False)
    final_elo.to_parquet(output_elo_path, index=False)

    return PrepareResult(
        matches_prepared=len(features),
        teams_rated=len(final_elo),
        output_dataset_path=output_dataset_path,
        output_elo_path=output_elo_path,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    result = prepare_dataset()
    logger.info(
        "Préparation terminée : %d match(s) préparé(s), %d équipe(s) notées -- %s, %s",
        result.matches_prepared,
        result.teams_rated,
        result.output_dataset_path,
        result.output_elo_path,
    )


if __name__ == "__main__":
    main()
