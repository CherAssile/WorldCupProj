from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AiPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    predicted_home_score: int
    predicted_away_score: int
    # True = prédiction de repli neutre (équipe non reconnue par le modèle) : le frontend
    # peut l'indiquer discrètement.
    is_fallback: bool
    created_at: datetime


class AiPredictionGenerationResult(BaseModel):
    created: int
    updated: int
    # Pronostics IA générés pour des matchs déjà joués n'en ayant pas encore (historique
    # manquant, comblé une seule fois par match -- jamais régénéré ensuite).
    backfilled: int
    skipped_unresolved_teams: int
    skipped_ai_unavailable: int
    # Prédictions de repli neutres servies faute d'équipe reconnue (ex. Curaçao).
    fallback_predictions: int
