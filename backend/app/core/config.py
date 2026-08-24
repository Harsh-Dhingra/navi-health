from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NAVI"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://navi:navi@localhost:5432/navi"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:3000"]

    document_storage_path: str = "./storage/documents"


@lru_cache
def get_settings() -> Settings:
    return Settings()
