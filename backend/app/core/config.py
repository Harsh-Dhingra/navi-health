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
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Comma-separated Fernet keys, newest first. Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    field_encryption_keys: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]
    cookie_secure: bool = True
    cookie_domain: str | None = None
    # "lax" works when frontend+backend share a registrable domain (e.g. app.x.com +
    # api.x.com, or localhost dev). On separate *.onrender.com subdomains with no
    # custom domain, browsers treat them as cross-site — set this to "none" there
    # (requires cookie_secure=true, which is the default).
    cookie_samesite: str = "lax"

    document_storage_path: str = "./storage/documents"
    max_upload_size_mb: int = 15

    # "mock" (default, safe for demos) or "availity" (requires real credentials)
    eligibility_provider: str = "mock"
    availity_api_key: str = ""
    availity_api_base_url: str = "https://api.availity.com"

    rate_limit_default: str = "60/minute"
    rate_limit_auth: str = "10/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
