from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application, lue depuis les variables d'environnement."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Pas de valeur par défaut pour un secret réel : une variable d'env manquante doit
    # faire échouer le démarrage plutôt que de faire tourner l'app avec une valeur connue
    # (cf. .env.example).
    database_url: str
    secret_key: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ai_service_url: str = "http://localhost:8001"
    cors_origins: str = "http://localhost:5173"
    football_api_key: str | None = None
    # Réinitialisation de mot de passe : backend d'envoi ("logging" en dev, fournisseur
    # réel au déploiement) et base des liens envoyés aux utilisateurs.
    email_backend: str = "logging"
    frontend_base_url: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()