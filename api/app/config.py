from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or api/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://orienta:orienta@localhost:5432/orienta"
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    # Sessions
    jwt_secret: str = "change-me"
    code_hmac_key: str = "change-me-too"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 604800
    cookie_secure: bool = False

    # Encryption (KEK_V<version> variables are read by app.crypto.keys)
    blind_index_key: str = ""  # 32 random bytes, base64
    # true: new messages are encrypted. false: stored in plain text, only to show the difference in a demo.
    encryption_enabled: bool = True

    # Verification codes and login protection (proposed values, see TDR section 4)
    verification_code_ttl_seconds: int = 600
    verification_max_attempts: int = 5
    verification_resend_cooldown_seconds: int = 60
    verification_max_resends_per_hour: int = 5
    auth_max_failed_logins: int = 5
    auth_lock_duration_seconds: int = 900

    # E-mails
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    mail_from: str = "Orienta <no-reply@orienta.local>"

    # Chatbot model
    llm_provider: str = "rodiumai"  # "rodiumai" or "fake"
    rodiumai_api_key: str | None = None
    rodiumai_model: str = "openai/gpt-4o"
    llm_timeout_seconds: float = 60
    triage_max_follow_up_questions: int = 4
    triage_red_flag_keywords: str = ""  # comma separated, to be validated by a health professional
    conversations_abandon_after_seconds: int = 86400

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
