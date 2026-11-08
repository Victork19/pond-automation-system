from datetime import datetime, timezone
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: str = 'development'
    database_url: str = 'sqlite:///./pond.db'
    operator_timezone: str = 'Europe/Paris'
    openai_api_key: str | None = None
    openai_model: str | None = None
    linkedin_read_enabled: bool = False
    gmail_send_enabled: bool = False
    x_provider: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = 'http://localhost:8000/api/integrations/google/callback'
    redis_url: str = 'redis://localhost:6379/0'
    celery_enabled: bool = False
    session_secret: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    cookie_secure: bool = False
    allowed_origins: str = ''
    trusted_hosts: str = ''
    google_token_encryption_key: str | None = None
    session_ttl_hours: int = 12

settings = Settings()

def now_utc() -> datetime:
    return datetime.now(timezone.utc)
