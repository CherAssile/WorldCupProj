# CLAUDE.md — WorldCupProj / Mundial Pronos

Contexte permanent du projet. Lis ce fichier avant toute tâche.
Place ce fichier à la racine du repo : Claude Code le lit depuis n'importe quel sous-dossier.

## Le produit

Application web de pronostics de la Coupe du monde assistée par IA. L'utilisateur
pronostique des matchs et des récompenses, se mesure aux autres, et peut s'entraîner
contre le moteur IA. Sert aussi de projet portfolio.

## Les deux modes de jeu (au cœur du produit)

1. **Compétitif — Joueur contre Joueur.**
   L'utilisateur pronostique les matchs à venir du tournoi. Les pronostics sont
   verrouillés côté serveur au coup d'envoi. Tout le monde est noté sur les vrais
   résultats et apparaît dans un **classement global unique** partagé. C'est le
   concours, avec enjeu.

2. **Entraînement — Joueur contre la Machine.**
   L'utilisateur pronostique des **matchs déjà joués** (Mondial en cours ou éditions
   passées) dont le résultat lui est **caché**. L'IA pronostique le même match. On
   révèle le vrai score et on note les deux avec le même barème. Rejouable à l'infini
   grâce au stock de matchs historiques. **Hors classement** : ce mode ne touche
   jamais au classement compétitif.

Règle d'or : un pronostic n'est jugé que face à un vrai résultat. Aucun hasard, aucun
tirage aléatoire pour noter un joueur.

## Isolation stricte (principe transversal)

Trois univers de données cloisonnés, aucune écriture ne traverse :
- **Compétitif** : `predictions`, `scores`, classement.
- **Entraînement** : `training_sessions`, `training_predictions`.
- **Simulation admin** : `simulation_runs`, `simulation_match_results`.
L'entraînement et les simulations ne modifient JAMAIS `predictions`, `scores` ni le
classement.

## Anti-triche (mode entraînement)

Le vrai score d'un match d'entraînement ne doit jamais partir vers le navigateur tant
que l'utilisateur n'a pas soumis son pronostic. Le résultat reste côté serveur, révélé
seulement après soumission. C'est l'équivalent du verrouillage au coup d'envoi du mode
compétitif.

## IA « point-in-time »

Quand l'IA pronostique un match (compétitif à venir OU match d'entraînement passé),
elle n'utilise que les informations disponibles AVANT ce match (classements, forme à
cette date). Elle ne connaît jamais le résultat. Sinon le duel n'aurait aucun sens.

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PostgreSQL, Redis, JWT,
httpx. Frontend React/TypeScript/Vite/Tailwind. Service IA séparé (FastAPI, port 8001).
Docker Compose. Tests pytest.

## Structure du repo

frontend/ (5173) · backend/ (8000, API principale) · ai-service/ (8001, prédictions)
· database/ · docs/ · docker-compose.yml

## Architecture du backend

```
backend/app/
  main.py · config.py · database.py · redis_client.py · deps.py
  core/security.py
  models/ · schemas/ · crud/ · routers/ · services/
```
Sépare les couches : un router appelle un service ou un crud, jamais de SQL direct dans
un router. Les schémas Pydantic ne sont jamais les modèles SQLAlchemy.

## Modèle de données (15 tables)

Core : users, teams, players, matches, historical_matches
Compétitif : predictions, ai_predictions, awards, award_predictions, scores
Entraînement : training_sessions, training_predictions
Simulation admin : simulation_runs, simulation_match_results

- `matches` : matchs du tournoi en cours (mode compétitif). Les équipes sont NULLABLES :
  un match de phase finale existe avant que ses participants soient connus (placeholders
  `W101` = vainqueur du match 101, `L102` = perdant du 102, résolus par la synchro).
- `historical_matches` : réserve de matchs passés au résultat connu (mode entraînement).
- `predictions` (compétitif) et `training_predictions` (entraînement) sont des tables
  SÉPARÉES : l'isolation est physique, pas un simple champ.

## Décisions métier

- Verrouillage compétitif : au coup d'envoi (`kickoff_at`), côté serveur, 409 si dépassé.
- **Score pronostiqué** : temps réglementaire (90 min + arrêts de jeu inclus), hors
  prolongation et tirs au but. C'est ce score, et lui seul, qui sert au scoring du score.
- **Qualifié pronostiqué** (matchs à élimination directe uniquement) : le joueur désigne
  aussi l'équipe qui passe au tour suivant. Le qualifié réel tient compte des
  prolongations et tirs au but. Sur un match de groupe, ce champ n'existe pas.
  Deux informations distinctes donc : `home_score`/`away_score` (temps réglementaire, pour
  le scoring) et `winner_team_id` (le qualifié, tous prolongements confondus, pour le
  bracket et la résolution des placeholders).
- **Barème** (entériné — le bon qualifié fait partie du barème officiel) :

  | Situation | Points |
  |---|---|
  | Score exact (temps réglementaire) | 3 |
  | Issue correcte (1/N/2), sans le score exact | 1 |
  | Bon qualifié (phases finales uniquement) | 2, **cumulables** avec les points de score |
  | Récompense correcte (buteur, passeur, joueur) | 5 |
  | Coefficient à partir des quarts de finale | **× 2** sur le total du match |

  Les deux composantes (score et qualifié) sont **indépendantes** : on peut se tromper sur
  le score et avoir le bon qualifié, et inversement. Le score se compare à
  `home_score`/`away_score` (temps réglementaire) ; le qualifié à `winner_team_id` (qui
  intègre prolongation et tirs au but).

  Exemple : match 74 Allemagne-Paraguay, 1-1 en 90 min, Paraguay qualifié aux tirs au but.
  Un pronostic « 1-1, Paraguay qualifié » = 3 (score exact) + 2 (bon qualifié) = **5 pts**.
  Le même pronostic en quart de finale ou au-delà = **10 pts**.

  Même barème en mode entraînement, pour départager joueur et IA — mais hors classement.
- Récompenses : meilleur buteur, passeur, joueur. Un pronostic par catégorie et par
  utilisateur, verrouillé à une date limite.
- Classement : GLOBAL et unique. Départage : total de points, puis nombre de scores
  exacts, puis date de création du compte. Les ligues privées entre amis sont en v2.
- L'IA peut apparaître comme concurrent dans le classement compétitif.

## Contrat backend ↔ ai-service

Le service IA est **autonome** : il ne connaît pas le schéma de la base du backend.

- Le backend lui envoie des **noms d'équipes** (`home_team`, `away_team`), jamais des IDs
  de sa base. Le modèle Elo/Poisson est entraîné sur un dataset historique où les équipes
  sont identifiées par leur nom — imposer les IDs du backend casserait l'isolation du
  service.
- Pour un match d'**entraînement** (match passé), le backend transmet en plus une **date de
  référence**. Le service IA ne calcule alors qu'avec les données antérieures à cette date
  (principe point-in-time). Sans cette date, l'IA « verrait le futur » et le duel n'aurait
  aucun sens.
- Le backend ne contient **aucune logique de modèle** : il appelle le service et persiste
  le résultat.

## Conventions de code

Type hints partout, Pydantic v2, SQLAlchemy 2.0 (Mapped). snake_case, tables au pluriel.
Codes HTTP corrects (401, 403, 404, 409, 422). Docstrings courtes en français. Aucun
secret en dur : tout par config.py / variables d'env.

## Workflow

- Environnement local : Windows / PowerShell. Donne les commandes dans cette syntaxe.
- Branche `develop`, jamais directement sur `main`.
- Un commit propre par tâche, Conventional Commits (feat, fix, chore, test). Propose le
  message, ne pousse pas sans validation.
- N'intègre PAS l'API Anthropic dans le produit pour l'instant : le service IA reste
  statistique. La couche LLM viendra plus tard.
- Écris un test pour toute règle sensible : verrouillage, anti-triche entraînement,
  scoring, isolation.

## Préconditions

PostgreSQL et Redis tournent via docker-compose. Variables d'env dans .env à la racine.

## Convention de commit

Format : type(scope): titre à l'impératif, max 72 caractères.
Corps obligatoire dès que le changement n'est pas trivial : d'abord le POURQUOI
(problème résolu, comportement constaté), puis la liste des changements techniques
(fichiers, colonnes, endpoints, règles, tests). Mentionner toute migration Alembic et
tout changement de schéma. Le corps doit permettre de comprendre le changement sans
lire le diff.