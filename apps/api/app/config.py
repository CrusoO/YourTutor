from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "tutor"
    postgres_password: str = "tutor"
    postgres_db: str = "yourtutor"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    redis_url: str = "redis://localhost:6379/0"
    allow_draft_content: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    otp_from_email: str = "noreply@localhost"
    otp_ttl_seconds: int = 600
    otp_request_limit_email: int = 3
    otp_request_limit_ip: int = 10
    otp_verify_limit_email: int = 5
    rate_window_seconds: int = 900
    pin_max_attempts: int = 5
    pin_lockout_seconds: int = 900
    pin_hash_iterations: int = 80_000
    session_ttl_seconds: int = 86_400
    token_pepper: str = "dev-only-change-me"
    test_database_url: str = ""
    reviewer_allowlist: str = ""
    otel_enabled: bool = False
    pilot_onboarding: bool = False
    pilot_key: str = "dev-pilot"
    e2e_mini_content: bool = False
    research_module: bool = False  # env: RESEARCH_MODULE=true
    jurisdiction_profile: str = "default_strict"  # env: JURISDICTION_PROFILE
    dev_tools: bool = False  # env: DEV_TOOLS (needs ALLOW_DRAFT_CONTENT too)
    cors_extra_origins: str = ""  # env: CORS_EXTRA_ORIGINS, comma separated (LAN preview)


settings = Settings()
