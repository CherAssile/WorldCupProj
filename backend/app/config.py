from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application, lue depuis les variables d'environnement."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mundial:changeme@localhost:5432/mundial_pronos"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "changeme-dev-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ai_service_url: str = "http://localhost:8001"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()