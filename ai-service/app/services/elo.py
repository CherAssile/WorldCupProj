"""Moteur de notation Elo, appliqué match par match dans l'ordre chronologique.

Chaque équipe démarre à 1500. Après chaque match, les deux notes sont mises à jour selon
le résultat réel et l'écart de niveau attendu (formule Elo standard, à somme nulle). Le
facteur K varie selon l'enjeu du match : plus élevé pour une compétition majeure (Coupe
du monde) que pour un match amical, où le résultat est statistiquement moins informatif.
"""
from __future__ import annotations

INITIAL_ELO = 1500.0

# Trois paliers, du moins au plus décisif -- un match amical met beaucoup moins à jour
# le niveau perçu d'une équipe qu'une victoire ou défaite en Coupe du monde.
K_FRIENDLY = 10.0
K_OFFICIAL = 20.0
K_WORLD_CUP = 40.0


def k_factor(tournament: str) -> float:
    """Amical < compétition officielle < Coupe du monde."""
    if tournament == "Friendly":
        return K_FRIENDLY
    if tournament == "FIFA World Cup":
        return K_WORLD_CUP
    return K_OFFICIAL


def expected_score(elo_a: float, elo_b: float) -> float:
    """Probabilité de victoire de A face à B (0.5 à niveau égal), formule Elo standard."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def actual_score(goals_for: int, goals_against: int) -> float:
    """1 (victoire), 0.5 (nul), 0 (défaite), au temps réglementaire du dataset source."""
    if goals_for > goals_against:
        return 1.0
    if goals_for < goals_against:
        return 0.0
    return 0.5


def update_ratings(
    elo_home: float, elo_away: float, home_score: int, away_score: int, tournament: str
) -> tuple[float, float]:
    """Nouvelles notes (domicile, extérieur) après ce match. Toujours à somme nulle : ce
    que l'une gagne, l'autre le perd exactement (propriété de base d'un système Elo)."""
    k = k_factor(tournament)
    expected_home = expected_score(elo_home, elo_away)
    actual_home = actual_score(home_score, away_score)

    delta = k * (actual_home - expected_home)
    return elo_home + delta, elo_away - delta
