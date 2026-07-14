"""Évaluation temporelle du modèle Dixon-Coles (A2).

Découpe le dataset préparé (A1) en deux blocs strictement séparés dans le temps :
entraînement (matchs antérieurs à la coupure) et test (matchs à partir de la coupure,
jamais vus à l'entraînement). PAS de split aléatoire : un split aléatoire mélangerait
passé et futur et créerait une fuite temporelle, donnant des résultats artificiellement
bons -- voir CLAUDE.md, la règle point-in-time s'applique aussi à l'évaluation, pas
seulement aux features.

Important : le modèle Dixon-Coles déjà sauvegardé sur disque (dixon_coles.load_model())
est entraîné sur la totalité du dataset, coupure comprise -- l'utiliser ici fuiterait
le test set dans l'entraînement. Ce module réajuste donc son propre modèle, uniquement
sur le bloc d'entraînement.

MÉTRIQUES :
- log-loss (référence : pénalise la confiance mal placée)
- score de Brier
- taux de bonnes issues (résultat 1N2)
- taux de scores exacts
- courbe de calibration (probabilités poolées des 3 issues, binned)

RÉFÉRENCES DE COMPARAISON :
1. le hasard : 33 % par issue, sans information.
2. favori Elo : l'équipe à l'Elo le plus élevé avant le match gagne toujours (jamais de
   nul) -- classifieur déterministe, pas de probabilités donc pas de log-loss/Brier.

Usage : python -m app.services.evaluation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from app.services import dixon_coles as dc

logger = logging.getLogger(__name__)

DEFAULT_SPLIT_DATE = pd.Timestamp("2024-01-01")
DEFAULT_CALIBRATION_BINS = 10
LOG_LOSS_EPS = 1e-15  # écrêtage anti -inf, valeur standard (cf. sklearn.metrics.log_loss)

REPORT_PATH = dc.DATA_DIR / "evaluation_report.txt"


def outcome_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def temporal_split(df: pd.DataFrame, split_date: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Découpe `df` en (entraînement, test) selon `split_date` : le test contient
    uniquement les matchs à partir de cette date (>=), l'entraînement uniquement les
    matchs strictement antérieurs (<). Jamais de recouvrement, jamais d'ordre aléatoire."""
    train = df[df["date"] < split_date].sort_values("date").reset_index(drop=True)
    test = df[df["date"] >= split_date].sort_values("date").reset_index(drop=True)
    if len(train) and len(test):
        assert train["date"].max() < test["date"].min(), "fuite temporelle : recouvrement train/test"
    return train, test


def predict_test_set(model: dc.DixonColesModel, test_df: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque match de `test_df`, calcule les probabilités d'issue et le score le
    plus probable selon `model`. `model` doit avoir été ajusté SANS voir ces matchs."""
    rows = []
    for match in test_df.itertuples():
        matrix = model.score_matrix(match.home_team, match.away_team)
        p_home, p_draw, p_away = dc.match_outcome_probabilities(matrix)
        pred_home_goals, pred_away_goals = dc.most_likely_score(matrix)
        rows.append(
            {
                "p_home_win": p_home,
                "p_draw": p_draw,
                "p_away_win": p_away,
                "pred_home_goals": pred_home_goals,
                "pred_away_goals": pred_away_goals,
                "actual_outcome": outcome_label(match.home_score, match.away_score),
                "actual_home_score": match.home_score,
                "actual_away_score": match.away_score,
            }
        )
    return pd.DataFrame(rows)


def log_loss(predictions: pd.DataFrame) -> float:
    """Moyenne de -log(p attribuée à l'issue réellement survenue), écrêtée pour éviter
    -inf si le modèle avait (à tort) attribué une probabilité nulle à l'issue réelle."""
    p_true = np.where(
        predictions["actual_outcome"] == "home_win",
        predictions["p_home_win"],
        np.where(predictions["actual_outcome"] == "draw", predictions["p_draw"], predictions["p_away_win"]),
    )
    p_true = np.clip(p_true, LOG_LOSS_EPS, 1.0)
    return float(-np.mean(np.log(p_true)))


def brier_score(predictions: pd.DataFrame) -> float:
    """Score de Brier multiclasse : moyenne, sur les matchs, de la somme des carrés des
    écarts entre probabilité prédite et réalisation (1 pour l'issue survenue, 0 sinon),
    sur les 3 issues."""
    is_home = (predictions["actual_outcome"] == "home_win").astype(float)
    is_draw = (predictions["actual_outcome"] == "draw").astype(float)
    is_away = (predictions["actual_outcome"] == "away_win").astype(float)
    squared_errors = (
        (predictions["p_home_win"] - is_home) ** 2
        + (predictions["p_draw"] - is_draw) ** 2
        + (predictions["p_away_win"] - is_away) ** 2
    )
    return float(squared_errors.mean())


def outcome_accuracy(predictions: pd.DataFrame) -> float:
    probs = predictions[["p_home_win", "p_draw", "p_away_win"]].to_numpy()
    labels = np.array(["home_win", "draw", "away_win"])
    predicted = labels[np.argmax(probs, axis=1)]
    return float((predicted == predictions["actual_outcome"].to_numpy()).mean())


def exact_score_accuracy(predictions: pd.DataFrame) -> float:
    correct = (predictions["pred_home_goals"] == predictions["actual_home_score"]) & (
        predictions["pred_away_goals"] == predictions["actual_away_score"]
    )
    return float(correct.mean())


def calibration_curve(predictions: pd.DataFrame, n_bins: int = DEFAULT_CALIBRATION_BINS) -> pd.DataFrame:
    """Regroupe les 3 flux de probabilités (p_home_win, p_draw, p_away_win), chacun
    apparié à la réalisation binaire correspondante (l'issue est-elle survenue ?), en un
    seul pool de N x 3 observations. Découpe ce pool en `n_bins` tranches de largeur
    égale sur [0, 1] : pour une calibration parfaite, la probabilité moyenne prédite
    d'une tranche doit être proche de la fréquence observée dans cette tranche."""
    pooled_prob = np.concatenate(
        [predictions["p_home_win"], predictions["p_draw"], predictions["p_away_win"]]
    )
    pooled_actual = np.concatenate(
        [
            (predictions["actual_outcome"] == "home_win").astype(float),
            (predictions["actual_outcome"] == "draw").astype(float),
            (predictions["actual_outcome"] == "away_win").astype(float),
        ]
    )

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Dernière tranche fermée des deux côtés ([0.9, 1.0]) pour inclure les proba == 1.0.
    bin_idx = np.digitize(pooled_prob, edges[1:-1], right=False)

    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                "bin_low": edges[b],
                "bin_high": edges[b + 1],
                "predicted_mean": float(pooled_prob[mask].mean()),
                "observed_frequency": float(pooled_actual[mask].mean()),
                "count": count,
            }
        )
    return pd.DataFrame(rows)


def random_baseline_metrics(predictions: pd.DataFrame) -> dict:
    """Référence 1 : le hasard, 33 % par issue, sans information. Les probabilités sont
    fixées à 1/3 pour reconstruire log-loss/Brier via les mêmes fonctions que le modèle
    (comparaison sur un pied d'égalité). L'exactitude, elle, N'EST PAS recalculée par
    argmax sur des probabilités égales : ce serait biaisé (argmax choisit toujours la
    première classe à égalité, donc refléterait la fréquence de home_win du jeu de test
    plutôt qu'un vrai hasard) -- elle vaut exactement 1/3 par construction (3 issues
    équiprobables)."""
    uniform = predictions.copy()
    uniform["p_home_win"] = 1.0 / 3.0
    uniform["p_draw"] = 1.0 / 3.0
    uniform["p_away_win"] = 1.0 / 3.0
    return {
        "log_loss": log_loss(uniform),
        "brier_score": brier_score(uniform),
        "outcome_accuracy": 1.0 / 3.0,
    }


def elo_favorite_baseline_metrics(test_df: pd.DataFrame) -> dict:
    """Référence 2 : l'équipe à l'Elo le plus élevé avant le match gagne toujours (jamais
    de nul prédit). Classifieur déterministe : pas de probabilités, donc log-loss/Brier
    non applicables (une probabilité 1/0 ferait diverger le log-loss dès la première
    erreur)."""
    predicted_home_win = test_df["elo_home_before"] >= test_df["elo_away_before"]
    actual_outcome = [
        outcome_label(h, a) for h, a in zip(test_df["home_score"], test_df["away_score"])
    ]
    predicted_outcome = np.where(predicted_home_win, "home_win", "away_win")
    accuracy = float((predicted_outcome == np.array(actual_outcome)).mean())
    return {"outcome_accuracy": accuracy}


@dataclass
class EvaluationResult:
    split_date: pd.Timestamp
    train_matches: int
    test_matches: int
    model_metrics: dict = field(default_factory=dict)
    random_metrics: dict = field(default_factory=dict)
    elo_metrics: dict = field(default_factory=dict)
    calibration: pd.DataFrame = field(default_factory=pd.DataFrame)


def evaluate(df: pd.DataFrame, split_date: pd.Timestamp = DEFAULT_SPLIT_DATE) -> EvaluationResult:
    train_df, test_df = temporal_split(df, split_date)
    if len(train_df) < 2 or len(test_df) < 1:
        raise ValueError("split_date laisse un jeu d'entraînement ou de test vide.")

    model = dc.fit(train_df)
    predictions = predict_test_set(model, test_df)

    return EvaluationResult(
        split_date=split_date,
        train_matches=len(train_df),
        test_matches=len(test_df),
        model_metrics={
            "log_loss": log_loss(predictions),
            "brier_score": brier_score(predictions),
            "outcome_accuracy": outcome_accuracy(predictions),
            "exact_score_accuracy": exact_score_accuracy(predictions),
        },
        random_metrics=random_baseline_metrics(predictions),
        elo_metrics=elo_favorite_baseline_metrics(test_df),
        calibration=calibration_curve(predictions),
    )


def format_report(result: EvaluationResult) -> str:
    m, r, e = result.model_metrics, result.random_metrics, result.elo_metrics
    lines = [
        "=== Évaluation temporelle du modèle Dixon-Coles ===",
        "",
        f"Coupure : entraînement < {result.split_date.date()} <= test",
        f"  Entraînement : {result.train_matches} match(s)",
        f"  Test         : {result.test_matches} match(s), jamais vus à l'entraînement",
        "",
        "--- Modèle Dixon-Coles ---",
        f"log-loss             : {m['log_loss']:.4f}",
        f"score de Brier        : {m['brier_score']:.4f}",
        f"taux de bonnes issues : {m['outcome_accuracy'] * 100:.1f} %  (attendu 50-55 %)",
        f"taux de scores exacts : {m['exact_score_accuracy'] * 100:.1f} %  (attendu 8-12 %)",
        "",
        "--- Référence 1 : hasard (33 % par issue) ---",
        f"log-loss             : {r['log_loss']:.4f}",
        f"score de Brier        : {r['brier_score']:.4f}",
        f"taux de bonnes issues : {r['outcome_accuracy'] * 100:.1f} %",
        "",
        "--- Référence 2 : favori Elo (gagne toujours, jamais de nul) ---",
        f"taux de bonnes issues : {e['outcome_accuracy'] * 100:.1f} %",
        "(log-loss / Brier non applicables : classifieur déterministe, pas de probabilités)",
        "",
        "--- Verdict ---",
        f"bat le hasard (log-loss) : {'OUI' if m['log_loss'] < r['log_loss'] else 'NON'}",
        f"bat le hasard (issues)   : {'OUI' if m['outcome_accuracy'] > r['outcome_accuracy'] else 'NON'}",
        f"bat le favori Elo (issues) : {'OUI' if m['outcome_accuracy'] > e['outcome_accuracy'] else 'NON'}",
        "",
        "--- Calibration (issues poolées home_win / draw / away_win) ---",
        f"{'tranche':<14}{'proba moyenne':<16}{'fréquence observée':<20}{'n':<8}",
    ]
    for row in result.calibration.itertuples():
        tranche = f"[{row.bin_low:.1f}-{row.bin_high:.1f}]"
        lines.append(f"{tranche:<14}{row.predicted_mean:<16.3f}{row.observed_frequency:<20.3f}{row.count:<8}")
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not dc.DEFAULT_PREPARED_DATASET_PATH.exists():
        raise SystemExit(
            f"{dc.DEFAULT_PREPARED_DATASET_PATH} introuvable : lancez d'abord "
            "python -m app.services.data_prep."
        )

    df = pd.read_parquet(dc.DEFAULT_PREPARED_DATASET_PATH)
    result = evaluate(df)
    report = format_report(result)
    print(report)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info("Rapport écrit : %s", REPORT_PATH)


if __name__ == "__main__":
    main()
