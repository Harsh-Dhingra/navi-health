import os

from cryptography.fernet import Fernet

os.environ.setdefault("FIELD_ENCRYPTION_KEYS", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://navi:navi@localhost:5432/navi_test")

from app.core.config import get_settings

get_settings.cache_clear()
