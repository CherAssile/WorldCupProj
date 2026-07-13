"""Simulation admin (bac à sable), mode réaliste uniquement.

Reconstitue un tournoi complet à partir du calendrier réel : les matchs déjà joués
gardent leur résultat réel (gelés), les matchs futurs sont simulés via le service IA.
Confort d'exploration pour l'admin -- CLAUDE.md, isolation stricte : ne lit
matches/teams que pour geler/simuler, n'écrit jamais dans matches/predictions/scores.
Seules simulation_runs et simulation_match_results sont persistées.

Pipeline : groupes (gel/simulation) -> classements -> tableau final (24 qualifiés
directs + 8 meilleurs 3es, la règle la plus complexe du format 2026) -> phase à
élimination directe (gel/simulation, tour par tour) -> finale.

Suppose le calendrier standard du projet (12 groupes de 4 = 48 équipes) : les autres
tailles de tournoi ne sont utiles qu'aux tests unitaires des fonctions de classement et
de tableau, prises isolément (cf. tests/test_simulation.py).
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, SimulationMode
from app.models.match import Match
from app.models.simulation_match_result import SimulationMatchResult
from app.models.simulation_run import SimulationRun
from app.models.team import Team
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)

# Format 2026 : 12 groupes de 4, les 2 premiers de chaque groupe PLUS les 8 meilleurs 3es
# (tous groupes confondus) sont qualifiés pour le tableau final (32 équipes).
BEST_THIRD_PLACED_QUALIFIERS = 8

# Ordre des tours à élimination directe une fois les 32 qualifiés connus. Fixe : ce module
# est scopé au calendrier standard du projet (12 groupes, cf. docstring).
KNOCKOUT_ROUND_ORDER: list[MatchPhase] = [
    MatchPhase.ROUND_OF_32,
    MatchPhase.ROUND_OF_16,
    MatchPhase.QUARTER_FINAL,
    MatchPhase.SEMI_FINAL,
    MatchPhase.FINAL,
]


class AIServiceUnavailable(Exception):
    """Le service IA est indisponible ou en erreur : la simulation s'arrête sans rien
    persister (jamais de tournoi partiellement simulé)."""


@dataclass(frozen=True)
class GroupMatchResult:
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int


@dataclass
class GroupStanding:
    group_name: str
    team_id: int
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn


@dataclass(frozen=True)
class SimulatedMatch:
    phase: MatchPhase
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    winner_team_id: int | None
    is_frozen_real_result: bool


def _standing_sort_key(standing: GroupStanding) -> tuple:
    return (-standing.points, -standing.goal_diff, -standing.goals_for, standing.team_id)


def compute_group_standings(group_name: str, results: list[GroupMatchResult]) -> list[GroupStanding]:
    """Classement d'un groupe à partir de ses résultats (réels et/ou simulés).

    Critères de départage : points, différence de buts, buts marqués, puis un repli
    déterministe (identifiant d'équipe). La confrontation directe (mini-classement entre
    équipes à égalité) n'est pas implémentée : simplification assumée pour un bac à sable
    de simulation.
    """
    standings: dict[int, GroupStanding] = {}

    def _get(team_id: int) -> GroupStanding:
        if team_id not in standings:
            standings[team_id] = GroupStanding(group_name=group_name, team_id=team_id)
        return standings[team_id]

    for result in results:
        home = _get(result.home_team_id)
        away = _get(result.away_team_id)
        home.played += 1
        away.played += 1
        home.goals_for += result.home_score
        home.goals_against += result.away_score
        away.goals_for += result.away_score
        away.goals_against += result.home_score
        if result.home_score > result.away_score:
            home.won += 1
            away.lost += 1
        elif result.home_score < result.away_score:
            away.won += 1
            home.lost += 1
        else:
            home.drawn += 1
            away.drawn += 1

    return sorted(standings.values(), key=_standing_sort_key)


def select_best_third_placed_teams(
    third_placed: list[GroupStanding], count: int = BEST_THIRD_PLACED_QUALIFIERS
) -> list[GroupStanding]:
    """Classement transversal des équipes classées 3es de leur groupe, tous groupes
    confondus : renvoie les `count` meilleures (8 par défaut, format 2026 à 12 groupes).

    C'est la règle la plus pénible du format 2026 : elle ne compare pas des équipes d'un
    même groupe mais les 3es de chacun des 12 groupes entre eux, avec les mêmes critères
    de départage que le classement de groupe (points, différence de buts, buts marqués),
    appliqués cette fois à travers tous les groupes. Fonction isolée et testée
    spécifiquement (cf. tests/test_simulation.py).
    """
    ranked = sorted(third_placed, key=_standing_sort_key)
    return ranked[:count]


def _pop_opponent_different_group(candidates: list[GroupStanding], excluded_group: str) -> GroupStanding:
    for index, candidate in enumerate(candidates):
        if candidate.group_name != excluded_group:
            return candidates.pop(index)
    # Repli (jamais atteint en format 2026, où 8 meilleurs 3es < 12 groupes) : plus aucun
    # candidat d'un groupe différent disponible, on autorise exceptionnellement un même
    # groupe plutôt que de planter -- ne peut survenir qu'avec un très petit nombre de
    # groupes (tests unitaires de cette fonction prise isolément).
    return candidates.pop(0)


def build_round_of_32_pairs(
    winners: list[GroupStanding], runners_up: list[GroupStanding], best_thirds: list[GroupStanding]
) -> list[tuple[int, int]]:
    """Construit les affrontements du tour préliminaire à partir des vainqueurs de groupe,
    des 2es et des meilleurs 3es qualifiés (16 affrontements pour 32 qualifiés en format
    standard : 12 vainqueurs + 12 2es + 8 meilleurs 3es).

    Simplification assumée : ne reproduit pas la table officielle FIFA d'affectation des
    3es aux barrages (dépend de la combinaison précise des groupes qualifiés, hors scope
    pour un bac à sable de simulation). Construit à la place un tableau déterministe et
    structurellement valide : jamais deux équipes du même groupe ne s'affrontent à ce tour.
    """
    remaining_winners = sorted(winners, key=lambda s: s.group_name)
    remaining_runners_up = sorted(runners_up, key=lambda s: s.group_name)
    thirds_sorted = sorted(best_thirds, key=_standing_sort_key)

    pairs: list[tuple[int, int]] = []

    # Les meilleurs 3es affrontent en priorité un vainqueur de groupe (jamais celui de leur
    # propre groupe).
    for third in thirds_sorted:
        opponent = _pop_opponent_different_group(remaining_winners, third.group_name)
        pairs.append((opponent.team_id, third.team_id))

    # Vainqueurs restants contre un 2e d'un groupe différent du leur.
    for winner in remaining_winners:
        opponent = _pop_opponent_different_group(remaining_runners_up, winner.group_name)
        pairs.append((winner.team_id, opponent.team_id))

    # 2es restants entre eux (jamais du même groupe : un groupe ne fournit qu'un seul 2e).
    while remaining_runners_up:
        a = remaining_runners_up.pop(0)
        b = remaining_runners_up.pop(0)
        pairs.append((a.team_id, b.team_id))

    return pairs


def _resolve_penalty_winner(seed: str, team_a_id: int, team_b_id: int) -> int:
    """Départage déterministe et reproductible en cas d'égalité simulée par l'IA, qui ne
    modélise pas les tirs au but (ai-service reste un mock statistique, cf. CLAUDE.md).
    Jamais utilisé pour un match gelé : le vrai résultat porte sa propre décision
    (Match.winner_team_id)."""
    a, b = sorted((team_a_id, team_b_id))
    digest = hashlib.sha256(f"{seed}:{a}:{b}".encode()).hexdigest()
    return a if int(digest, 16) % 2 == 0 else b


def _team_group_map(db: Session) -> dict[int, str]:
    return {team.id: team.group_name for team in db.execute(select(Team)).scalars() if team.group_name is not None}


def _real_results_by_phase_and_pair(db: Session) -> dict[tuple[MatchPhase, frozenset[int]], Match]:
    """Tous les matchs réels déjà joués, indexés par (phase, paire d'équipes) -- la phase
    fait partie de la clé pour ne jamais confondre deux équipes qui s'affronteraient deux
    fois dans le tournoi (ex. en groupes puis à nouveau en phase finale)."""
    stmt = select(Match).where(
        Match.home_score.is_not(None), Match.home_team_id.is_not(None), Match.away_team_id.is_not(None)
    )
    lookup: dict[tuple[MatchPhase, frozenset[int]], Match] = {}
    for match in db.execute(stmt).scalars():
        key = (match.phase, frozenset((match.home_team_id, match.away_team_id)))
        lookup[key] = match
    return lookup


def _simulate_group_phase(
    db: Session,
    ai_client: AIClient,
    team_groups: dict[int, str],
) -> tuple[list[SimulatedMatch], dict[str, list[GroupMatchResult]]]:
    """Un match de groupe déjà joué garde son résultat réel (gelé) ; un match à venir est
    simulé via le service IA. Les deux équipes sont toujours connues dès le tirage au sort
    (jamais de placeholder en phase de groupes)."""
    stmt = select(Match).where(Match.phase == MatchPhase.GROUP).order_by(Match.kickoff_at)
    matches = list(db.execute(stmt).scalars())

    simulated: list[SimulatedMatch] = []
    by_group: dict[str, list[GroupMatchResult]] = {}

    for match in matches:
        if match.home_team_id is None or match.away_team_id is None:
            continue  # garde de prudence : ne devrait jamais arriver en phase de groupes

        if match.home_score is not None:
            home_score, away_score = match.home_score, match.away_score
            is_frozen = True
        else:
            prediction = ai_client.predict_match(match.home_team_id, match.away_team_id, match.id)
            if prediction is None:
                raise AIServiceUnavailable(f"Service IA indisponible pour le match {match.id} (groupe).")
            home_score, away_score = prediction.predicted_home_score, prediction.predicted_away_score
            is_frozen = False

        simulated.append(
            SimulatedMatch(
                phase=MatchPhase.GROUP,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                home_score=home_score,
                away_score=away_score,
                winner_team_id=None,
                is_frozen_real_result=is_frozen,
            )
        )

        group_name = team_groups.get(match.home_team_id)
        if group_name is not None:
            by_group.setdefault(group_name, []).append(
                GroupMatchResult(match.home_team_id, match.away_team_id, home_score, away_score)
            )

    return simulated, by_group


def _simulate_knockout_match(
    phase: MatchPhase,
    home_team_id: int,
    away_team_id: int,
    real_results: dict[tuple[MatchPhase, frozenset[int]], Match],
    ai_client: AIClient,
    tie_break_seed: str,
) -> SimulatedMatch:
    """Si ce même affrontement, à ce même tour, a déjà réellement eu lieu, garde son
    résultat réel (gelé) -- sinon le simule via le service IA."""
    key = (phase, frozenset((home_team_id, away_team_id)))
    real_match = real_results.get(key)
    if real_match is not None:
        winner_id = real_match.winner_team_id
        if winner_id is None:
            # Garde défensive : un match à élimination directe FINISHED a toujours un
            # vainqueur en base (cf. seed du calendrier) ; ne devrait pas arriver.
            winner_id = home_team_id if real_match.home_score >= real_match.away_score else away_team_id
        return SimulatedMatch(
            phase=phase,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=real_match.home_score,
            away_score=real_match.away_score,
            winner_team_id=winner_id,
            is_frozen_real_result=True,
        )

    prediction = ai_client.predict_match(home_team_id, away_team_id)
    if prediction is None:
        raise AIServiceUnavailable(
            f"Service IA indisponible pour {home_team_id} vs {away_team_id} ({phase.value})."
        )

    home_score, away_score = prediction.predicted_home_score, prediction.predicted_away_score
    if home_score > away_score:
        winner_id = home_team_id
    elif away_score > home_score:
        winner_id = away_team_id
    else:
        winner_id = _resolve_penalty_winner(tie_break_seed, home_team_id, away_team_id)

    return SimulatedMatch(
        phase=phase,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_score=home_score,
        away_score=away_score,
        winner_team_id=winner_id,
        is_frozen_real_result=False,
    )


def run_realistic_simulation(
    db: Session,
    created_by_user_id: int,
    label: str | None = None,
    ai_client: AIClient | None = None,
) -> SimulationRun:
    """Simule un tournoi complet en mode réaliste (seul mode implémenté) : matchs déjà
    joués gelés à leur résultat réel, matchs futurs simulés via le service IA.

    Calcule tout en mémoire avant de rien persister : si le service IA devient
    indisponible en cours de route, `AIServiceUnavailable` est levée et rien n'est écrit
    (jamais de tournoi partiellement simulé). Un seul commit, à la toute fin.
    """
    ai_client = ai_client or AIClient()
    tie_break_seed = uuid.uuid4().hex

    team_groups = _team_group_map(db)
    real_results = _real_results_by_phase_and_pair(db)

    simulated_matches, group_results = _simulate_group_phase(db, ai_client, team_groups)

    winners: list[GroupStanding] = []
    runners_up: list[GroupStanding] = []
    thirds: list[GroupStanding] = []
    for group_name, results in group_results.items():
        standings = compute_group_standings(group_name, results)
        if len(standings) < 3:
            continue  # groupe incomplet : pas de 3e à qualifier (scénario de test réduit)
        winners.append(standings[0])
        runners_up.append(standings[1])
        thirds.append(standings[2])

    best_thirds = select_best_third_placed_teams(thirds, count=min(BEST_THIRD_PLACED_QUALIFIERS, len(thirds)))
    if len(best_thirds) % 2 != 0:
        best_thirds = best_thirds[:-1]  # nombre pair requis pour un tableau valide

    current_pairs = build_round_of_32_pairs(winners, runners_up, best_thirds)

    for phase in KNOCKOUT_ROUND_ORDER:
        round_matches = [
            _simulate_knockout_match(phase, home_id, away_id, real_results, ai_client, tie_break_seed)
            for home_id, away_id in current_pairs
        ]
        simulated_matches.extend(round_matches)

        winner_ids = [m.winner_team_id for m in round_matches]

        if phase == MatchPhase.SEMI_FINAL:
            # Petite finale : les deux perdants des demies, en parallèle du tableau
            # principal (ne modifie pas la progression winner_ids -> current_pairs).
            loser_ids = [
                m.away_team_id if m.winner_team_id == m.home_team_id else m.home_team_id for m in round_matches
            ]
            third_place_match = _simulate_knockout_match(
                MatchPhase.THIRD_PLACE, loser_ids[0], loser_ids[1], real_results, ai_client, tie_break_seed
            )
            simulated_matches.append(third_place_match)

        if phase == MatchPhase.FINAL:
            break
        current_pairs = [(winner_ids[i], winner_ids[i + 1]) for i in range(0, len(winner_ids), 2)]

    run = SimulationRun(created_by_user_id=created_by_user_id, mode=SimulationMode.REALISTIC, label=label)
    db.add(run)
    db.flush()

    for sim in simulated_matches:
        db.add(
            SimulationMatchResult(
                simulation_run_id=run.id,
                home_team_id=sim.home_team_id,
                away_team_id=sim.away_team_id,
                phase=sim.phase,
                simulated_home_score=sim.home_score,
                simulated_away_score=sim.away_score,
                winner_team_id=sim.winner_team_id,
                is_frozen_real_result=sim.is_frozen_real_result,
            )
        )

    db.commit()
    db.refresh(run)
    return run
