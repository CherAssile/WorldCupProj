"""Libellés lisibles des placeholders de phase finale, résolus d'un niveau.

Le format source (openfootball) est `W<num>` (vainqueur du match num) ou `L<num>`
(perdant). Quand le match référencé a ses deux équipes connues, on remonte d'un niveau :
« W101 » avec la demie 101 = France-Espagne devient « France ou Espagne » plutôt que le
« Vainqueur du match 101 » exact mais inutilisable. Le frontend n'a jamais à remonter la
chaîne des placeholders lui-même.

La résolution a besoin de l'ensemble des matchs (pour retrouver le match `num`) : elle
vit donc ici, appelée par le router qui dispose de la collection complète, et non dans un
champ calculé de MatchRead (qui ne voit qu'un match isolé).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.match import Match
from app.services.team_names_fr import french_team_name

_PLACEHOLDER_PATTERN = re.compile(r"^([WL])(\d+)$")


@dataclass(frozen=True)
class PlaceholderLabels:
    """Deux libellés d'un même placeholder : long (« France ou Espagne ») et court
    (« FRA/ESP »), pour les emplacements contraints en largeur."""

    long: str | None
    short: str | None


def _reference(code: str | None) -> tuple[str, int] | None:
    """(« W »|« L », num) d'un placeholder, ou None si ce n'en est pas un."""
    if code is None:
        return None
    match = _PLACEHOLDER_PATTERN.match(code)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def resolve_placeholder(code: str | None, matches_by_num: dict[int, Match]) -> PlaceholderLabels:
    """Résout un placeholder d'un niveau contre l'ensemble des matchs (indexés par num).

    - Match référencé aux deux équipes connues : « France ou Espagne » / « FRA/ESP »
      (« Perdant France-Espagne » / « Perdant FRA/ESP » pour un placeholder de type L).
    - Match référencé inconnu ou aux équipes encore inconnues : repli sur
      « Vainqueur du match 101 » / « V. 101 ».
    - Code None → labels None ; code au format inattendu → renvoyé brut.
    """
    reference = _reference(code)
    if reference is None:
        return PlaceholderLabels(long=code, short=code) if code is not None else PlaceholderLabels(None, None)

    kind, num = reference
    match = matches_by_num.get(num)
    if match is not None and match.home_team is not None and match.away_team is not None:
        # Traduit pour la phrase affichée uniquement : Team.name (anglais, source) n'est
        # jamais modifié -- c'est lui qui sert au contrat avec ai-service.
        home_name = french_team_name(match.home_team.name)
        away_name = french_team_name(match.away_team.name)
        home_code, away_code = match.home_team.fifa_code, match.away_team.fifa_code
        if kind == "W":
            return PlaceholderLabels(
                long=f"{home_name} ou {away_name}",
                short=f"{home_code}/{away_code}",
            )
        return PlaceholderLabels(
            long=f"Perdant {home_name}-{away_name}",
            short=f"Perdant {home_code}/{away_code}",
        )

    if kind == "W":
        return PlaceholderLabels(long=f"Vainqueur du match {num}", short=f"V. {num}")
    return PlaceholderLabels(long=f"Perdant du match {num}", short=f"P. {num}")
