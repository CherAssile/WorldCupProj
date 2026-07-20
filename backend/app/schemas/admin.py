from pydantic import BaseModel


class FullSyncResultRead(BaseModel):
    """Résumé de la chaîne complète de synchronisation (calendrier, placeholders, scores,
    classement) -- identique que la chaîne ait été déclenchée par le scheduler ou par
    POST /admin/sync."""

    teams_created: int
    matches_created: int
    matches_updated: int
    placeholders_resolved: int
    scores_recalculated: int
    leaderboard_size: int
