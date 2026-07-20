/**
 * Traduction d'affichage des noms d'équipes (anglais -> français).
 *
 * La source (openfootball) fournit des noms en anglais (TeamRead.name) : cette table ne
 * sert qu'à l'affichage. Équipes dont le nom est identique dans les deux langues (France,
 * Canada, Portugal...) omises : le repli renvoie le nom source inchangé.
 * Doit rester synchronisée avec backend/app/services/team_names_fr.py (même dataset,
 * même logique, dupliquée car ce n'est ni une donnée du contrat API ni amenée à changer).
 */
const FRENCH_TEAM_NAMES: Record<string, string> = {
  Algeria: "Algérie",
  Argentina: "Argentine",
  Australia: "Australie",
  Austria: "Autriche",
  Belgium: "Belgique",
  "Bosnia & Herzegovina": "Bosnie-Herzégovine",
  Brazil: "Brésil",
  "Cape Verde": "Cap-Vert",
  Colombia: "Colombie",
  Croatia: "Croatie",
  "Czech Republic": "République tchèque",
  "DR Congo": "RD Congo",
  Ecuador: "Équateur",
  Egypt: "Égypte",
  England: "Angleterre",
  Germany: "Allemagne",
  Haiti: "Haïti",
  Iraq: "Irak",
  "Ivory Coast": "Côte d'Ivoire",
  Japan: "Japon",
  Jordan: "Jordanie",
  Mexico: "Mexique",
  Morocco: "Maroc",
  Netherlands: "Pays-Bas",
  "New Zealand": "Nouvelle-Zélande",
  Norway: "Norvège",
  "Saudi Arabia": "Arabie saoudite",
  Scotland: "Écosse",
  Senegal: "Sénégal",
  "South Africa": "Afrique du Sud",
  "South Korea": "Corée du Sud",
  Spain: "Espagne",
  Sweden: "Suède",
  Switzerland: "Suisse",
  Tunisia: "Tunisie",
  Turkey: "Turquie",
  USA: "États-Unis",
  Uzbekistan: "Ouzbékistan",
};

/** Nom d'équipe en français pour l'affichage ; le nom source si pas de traduction connue. */
export function frenchTeamName(name: string): string {
  return FRENCH_TEAM_NAMES[name] ?? name;
}
