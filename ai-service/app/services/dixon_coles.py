"""Modèle de Poisson bivarié -- approche Dixon-Coles (1997).

Chaque équipe a une force offensive (attack) et une force défensive (defense), plus un
avantage du terrain commun (home_advantage). Le nombre de buts de chaque équipe suit une
loi de Poisson dont le paramètre lambda dépend de l'attaque de l'une et de la défense de
l'autre :

    lambda_home = exp(attack_home + defense_away + home_advantage)
    lambda_away = exp(attack_away + defense_home)

Une fois les lambdas connus, la matrice des scores probables se calcule directement :
P(score = i-j) = Poisson(i, lambda_home) x Poisson(j, lambda_away), corrigée par tau()
pour les scores faibles (0-0, 1-0, 0-1, 1-1) que le Poisson non corrélé sous-estime
systématiquement (corrélation négative observée entre les deux scores sur ces cases).

Entraîné sur le dataset préparé par data_prep.py (A1). `fit(..., as_of_date=...)`
respecte strictement le point-in-time : aucun match de date postérieure OU ÉGALE à la
coupure n'est utilisé -- indispensable pour ne jamais entraîner le modèle sur des
résultats qu'il n'aurait pas encore pu connaître au moment de prédire.

Usage : python -m app.services.dixon_coles
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_PREPARED_DATASET_PATH = DATA_DIR / "prepared_matches.parquet"
DEFAULT_RATINGS_OUTPUT_PATH = DATA_DIR / "dixon_coles_team_ratings.parquet"
DEFAULT_PARAMS_OUTPUT_PATH = DATA_DIR / "dixon_coles_global_params.json"

DEFAULT_MAX_GOALS = 10


def tau(x: int, y: int, lambda_home: float, lambda_away: float, rho: float) -> float:
    """Correction Dixon-Coles : vaut 1 (aucun effet) partout sauf sur les 4 scores
    faibles, où un Poisson non corrélé sous-estime systématiquement la fréquence
    observée."""
    if x == 0 and y == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if x == 0 and y == 1:
        return 1.0 + lambda_home * rho
    if x == 1 and y == 0:
        return 1.0 + lambda_away * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(
    lambda_home: float, lambda_away: float, rho: float, max_goals: int = DEFAULT_MAX_GOALS
) -> np.ndarray:
    """Matrice (max_goals+1) x (max_goals+1) : case [i, j] = P(domicile marque i ET
    extérieur marque j). Toujours renormalisée pour sommer exactement à 1 -- la
    troncature à max_goals laisse échapper une masse de probabilité infime mais non
    nulle dans la queue, et rho peut en théorie faire légèrement passer une case sous 0
    (corrigé par clip avant renormalisation)."""
    goals = np.arange(max_goals + 1)
    home_pmf = poisson.pmf(goals, lambda_home)
    away_pmf = poisson.pmf(goals, lambda_away)
    matrix = np.outer(home_pmf, away_pmf)

    for i in range(2):
        for j in range(2):
            matrix[i, j] *= tau(i, j, lambda_home, lambda_away, rho)

    matrix = np.clip(matrix, a_min=0.0, a_max=None)
    return matrix / matrix.sum()


def match_outcome_probabilities(matrix: np.ndarray) -> tuple[float, float, float]:
    """(P victoire domicile, P nul, P victoire extérieur), à partir de la matrice des
    scores : case [i, j] = P(domicile marque i, extérieur marque j)."""
    home_win = float(np.tril(matrix, k=-1).sum())  # i > j : plus de buts à domicile
    draw = float(np.trace(matrix))  # i == j
    away_win = float(np.triu(matrix, k=1).sum())  # i < j
    return home_win, draw, away_win


def most_likely_score(matrix: np.ndarray) -> tuple[int, int]:
    """Case de probabilité maximale de la matrice des scores."""
    home_goals, away_goals = np.unravel_index(np.argmax(matrix), matrix.shape)
    return int(home_goals), int(away_goals)


def _neg_log_likelihood(
    params: np.ndarray,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    n_teams: int,
) -> float:
    """Vectorisée (numpy, aucune boucle Python sur les matchs) : indispensable pour que
    l'optimisation reste rapide même avec plusieurs centaines d'équipes et dizaines de
    milliers de matchs, l'objectif étant évalué à chaque itération.

    L'équipe de référence (index 0) a une attaque et une défense fixées à 0 : sans cette
    contrainte, le modèle ne serait identifiable qu'à une translation globale près
    (attack += c, defense -= c pour toutes les équipes laisse les lambdas inchangés).
    """
    attack = np.concatenate(([0.0], params[: n_teams - 1]))
    defense = np.concatenate(([0.0], params[n_teams - 1 : 2 * (n_teams - 1)]))
    home_advantage = params[-2]
    rho = params[-1]

    # Écrêté (log-espace) : L-BFGS-B explore parfois des valeurs de paramètres extrêmes
    # pendant sa recherche de pas (finite differences), avant de reconverger vers des
    # valeurs raisonnables. Sans ce garde-fou, exp() déborde vers +inf ou 0 exact, et le
    # log() qui suit produit des NaN qui perturbent inutilement l'optimiseur.
    log_lambda_home = np.clip(attack[home_idx] + defense[away_idx] + home_advantage, -20.0, 20.0)
    log_lambda_away = np.clip(attack[away_idx] + defense[home_idx], -20.0, 20.0)
    lambda_home = np.exp(log_lambda_home)
    lambda_away = np.exp(log_lambda_away)

    # log-vraisemblance Poisson, forme stable numériquement (évite de calculer k! directement,
    # et réutilise log(lambda) déjà calculé ci-dessus plutôt que de reprendre log(exp(.))).
    log_lik = (
        home_goals * log_lambda_home - lambda_home - gammaln(home_goals + 1)
        + away_goals * log_lambda_away - lambda_away - gammaln(away_goals + 1)
    )

    tau_values = np.ones_like(log_lik)
    mask_00 = (home_goals == 0) & (away_goals == 0)
    mask_01 = (home_goals == 0) & (away_goals == 1)
    mask_10 = (home_goals == 1) & (away_goals == 0)
    mask_11 = (home_goals == 1) & (away_goals == 1)
    tau_values[mask_00] = 1.0 - lambda_home[mask_00] * lambda_away[mask_00] * rho
    tau_values[mask_01] = 1.0 + lambda_home[mask_01] * rho
    tau_values[mask_10] = 1.0 + lambda_away[mask_10] * rho
    tau_values[mask_11] = 1.0 - rho
    # Garde-fou pendant l'optimisation : un rho extrême (avant convergence) pourrait
    # rendre tau <= 0 sur une case, ce qui ferait diverger log(). Jamais atteint au
    # voisinage de l'optimum (rho y reste petit).
    tau_values = np.clip(tau_values, 1e-10, None)

    log_lik = log_lik + np.log(tau_values)
    return -float(np.sum(log_lik))


@dataclass
class DixonColesModel:
    attack: dict[str, float]
    defense: dict[str, float]
    home_advantage: float
    rho: float
    reference_team: str
    fitted_matches: int

    def rates(self, home_team: str, away_team: str) -> tuple[float, float]:
        """(lambda_home, lambda_away) pour cet affrontement. Une équipe inconnue du
        modèle est traitée comme une équipe de force moyenne (attaque et défense à 0)."""
        if home_team not in self.attack:
            logger.warning("Équipe inconnue du modèle Dixon-Coles, force moyenne utilisée : %s", home_team)
        if away_team not in self.attack:
            logger.warning("Équipe inconnue du modèle Dixon-Coles, force moyenne utilisée : %s", away_team)

        attack_home = self.attack.get(home_team, 0.0)
        defense_home = self.defense.get(home_team, 0.0)
        attack_away = self.attack.get(away_team, 0.0)
        defense_away = self.defense.get(away_team, 0.0)

        lambda_home = float(np.exp(attack_home + defense_away + self.home_advantage))
        lambda_away = float(np.exp(attack_away + defense_home))
        return lambda_home, lambda_away

    def score_matrix(self, home_team: str, away_team: str, max_goals: int = DEFAULT_MAX_GOALS) -> np.ndarray:
        lambda_home, lambda_away = self.rates(home_team, away_team)
        return score_matrix(lambda_home, lambda_away, self.rho, max_goals)


def fit(df: pd.DataFrame, as_of_date: pd.Timestamp | str | None = None) -> DixonColesModel:
    """Ajuste le modèle par maximum de vraisemblance sur `df` (colonnes attendues :
    date, home_team, away_team, home_score, away_score).

    `as_of_date`, si fourni, exclut tout match de date postérieure OU ÉGALE avant
    l'ajustement : condition nécessaire au respect strict du point-in-time quand ce
    modèle sert à prédire un match à une date donnée -- jamais entraîné sur des résultats
    qu'il n'aurait pas encore pu connaître à ce moment-là.
    """
    if as_of_date is not None:
        df = df[df["date"] < pd.Timestamp(as_of_date)]
    df = df.reset_index(drop=True)

    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    n_teams = len(teams)
    if n_teams < 2:
        raise ValueError("Impossible d'ajuster le modèle : moins de 2 équipes dans les données fournies.")
    team_index = {team: i for i, team in enumerate(teams)}
    reference_team = teams[0]

    home_idx = df["home_team"].map(team_index).to_numpy()
    away_idx = df["away_team"].map(team_index).to_numpy()
    home_goals = df["home_score"].to_numpy(dtype=float)
    away_goals = df["away_score"].to_numpy(dtype=float)

    n_free = 2 * (n_teams - 1) + 2  # attaques + défenses (hors référence) + home_adv + rho
    initial_params = np.zeros(n_free)

    result = minimize(
        _neg_log_likelihood,
        initial_params,
        args=(home_idx, away_idx, home_goals, away_goals, n_teams),
        method="L-BFGS-B",
        # maxfun par défaut (15000) est vite atteint avec plusieurs centaines de
        # paramètres (chaque évaluation de gradient par différences finies en consomme
        # n_free). Relevé, mais sans viser la convergence stricte à cette échelle : sur
        # les ~330 équipes du dataset complet, la tolérance par défaut de L-BFGS-B n'est
        # pas atteinte avant plusieurs minutes pour un gain de vraisemblance marginal --
        # au-delà de ce budget, on accepte un optimum proche plutôt que d'attendre une
        # convergence exacte (les classements produits restent stables et cohérents,
        # cf. tests avec des championnats synthétiques qui, eux, convergent pleinement).
        options={"maxiter": 300, "maxfun": 50_000},
    )
    if not result.success:
        logger.warning("Optimisation Dixon-Coles non pleinement convergée : %s", result.message)

    params = result.x
    attack = np.concatenate(([0.0], params[: n_teams - 1]))
    defense = np.concatenate(([0.0], params[n_teams - 1 : 2 * (n_teams - 1)]))

    return DixonColesModel(
        attack=dict(zip(teams, attack.tolist())),
        defense=dict(zip(teams, defense.tolist())),
        home_advantage=float(params[-2]),
        rho=float(params[-1]),
        reference_team=reference_team,
        fitted_matches=len(df),
    )


def save_model(
    model: DixonColesModel,
    ratings_path: Path = DEFAULT_RATINGS_OUTPUT_PATH,
    params_path: Path = DEFAULT_PARAMS_OUTPUT_PATH,
) -> None:
    ratings_path.parent.mkdir(parents=True, exist_ok=True)
    ratings = pd.DataFrame(
        {
            "team": list(model.attack.keys()),
            "attack": list(model.attack.values()),
            "defense": [model.defense[team] for team in model.attack],
        }
    )
    ratings.to_parquet(ratings_path, index=False)

    params_path.write_text(
        json.dumps(
            {
                "home_advantage": model.home_advantage,
                "rho": model.rho,
                "reference_team": model.reference_team,
                "fitted_matches": model.fitted_matches,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_model(
    ratings_path: Path = DEFAULT_RATINGS_OUTPUT_PATH, params_path: Path = DEFAULT_PARAMS_OUTPUT_PATH
) -> DixonColesModel:
    ratings = pd.read_parquet(ratings_path)
    params = json.loads(params_path.read_text(encoding="utf-8"))
    return DixonColesModel(
        attack=dict(zip(ratings["team"], ratings["attack"])),
        defense=dict(zip(ratings["team"], ratings["defense"])),
        home_advantage=params["home_advantage"],
        rho=params["rho"],
        reference_team=params["reference_team"],
        fitted_matches=params["fitted_matches"],
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not DEFAULT_PREPARED_DATASET_PATH.exists():
        raise SystemExit(
            f"{DEFAULT_PREPARED_DATASET_PATH} introuvable : lancez d'abord "
            "python -m app.services.data_prep."
        )

    df = pd.read_parquet(DEFAULT_PREPARED_DATASET_PATH)
    model = fit(df)
    save_model(model)
    logger.info(
        "Modèle Dixon-Coles entraîné sur %d match(s), %d équipe(s) -- "
        "avantage du terrain=%.3f, rho=%.4f -- %s, %s",
        model.fitted_matches,
        len(model.attack),
        model.home_advantage,
        model.rho,
        DEFAULT_RATINGS_OUTPUT_PATH,
        DEFAULT_PARAMS_OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
