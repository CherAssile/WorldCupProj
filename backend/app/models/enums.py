from enum import Enum


class MatchPhase(str, Enum):
    """Phase du tournoi. Sert aussi au multiplicateur de barème (x2 à partir des quarts)."""

    GROUP = "group"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class MatchStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"


class AwardCategory(str, Enum):
    TOP_SCORER = "top_scorer"
    TOP_ASSIST = "top_assist"
    BEST_PLAYER = "best_player"
