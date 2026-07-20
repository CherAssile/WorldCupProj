"""Traduction d'affichage des noms d'équipes (anglais -> français).

La source (openfootball) et le contrat avec ai-service utilisent des noms en anglais
(Team.name, jamais modifié) : cette table ne sert qu'à composer un texte lisible en
français (ex. les libellés de placeholders, cf. services/placeholders.py). Équipes dont
le nom est identique dans les deux langues (France, Canada, Portugal...) omises : le
repli renvoie le nom source inchangé.
"""
from __future__ import annotations

_FRENCH_TEAM_NAMES: dict[str, str] = {
    "Algeria": "Algérie",
    "Argentina": "Argentine",
    "Australia": "Australie",
    "Austria": "Autriche",
    "Belgium": "Belgique",
    "Bosnia & Herzegovina": "Bosnie-Herzégovine",
    "Brazil": "Brésil",
    "Cape Verde": "Cap-Vert",
    "Colombia": "Colombie",
    "Croatia": "Croatie",
    "Czech Republic": "République tchèque",
    "DR Congo": "RD Congo",
    "Ecuador": "Équateur",
    "Egypt": "Égypte",
    "England": "Angleterre",
    "Germany": "Allemagne",
    "Haiti": "Haïti",
    "Iraq": "Irak",
    "Ivory Coast": "Côte d'Ivoire",
    "Japan": "Japon",
    "Jordan": "Jordanie",
    "Mexico": "Mexique",
    "Morocco": "Maroc",
    "Netherlands": "Pays-Bas",
    "New Zealand": "Nouvelle-Zélande",
    "Norway": "Norvège",
    "Saudi Arabia": "Arabie saoudite",
    "Scotland": "Écosse",
    "Senegal": "Sénégal",
    "South Africa": "Afrique du Sud",
    "South Korea": "Corée du Sud",
    "Spain": "Espagne",
    "Sweden": "Suède",
    "Switzerland": "Suisse",
    "Tunisia": "Tunisie",
    "Turkey": "Turquie",
    "USA": "États-Unis",
    "Uzbekistan": "Ouzbékistan",
}


def french_team_name(name: str) -> str:
    """Nom d'équipe en français pour l'affichage ; le nom source si pas de traduction connue."""
    return _FRENCH_TEAM_NAMES.get(name, name)
