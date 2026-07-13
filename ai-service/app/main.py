from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mundial Pronos AI Service")


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que le service IA est opérationnel."""
    return {"status": "ok"}


class MatchPredictionRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    match_id: int | None = None


class MatchPredictionResponse(BaseModel):
    predicted_home_score: int
    predicted_away_score: int


@app.post("/predict-match", response_model=MatchPredictionResponse)
def predict_match(request: MatchPredictionRequest) -> MatchPredictionResponse:
    """Prédiction simulée (mock), déterministe. Le vrai modèle statistique point-in-time
    (CLAUDE.md) arrivera dans une tâche ultérieure ; ceci ne fait qu'exposer une réponse
    stable pour développer et tester le client côté backend."""
    return MatchPredictionResponse(
        predicted_home_score=(request.home_team_id + request.away_team_id) % 4,
        predicted_away_score=(request.home_team_id * 2 + request.away_team_id) % 3,
    )