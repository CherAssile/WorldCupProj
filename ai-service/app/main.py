from fastapi import FastAPI

app = FastAPI(title="Mundial Pronos AI Service")


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que le service IA est opérationnel."""
    return {"status": "ok"}