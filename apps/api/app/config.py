from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "tutor"
    postgres_password: str = "tutor"
    postgres_db: str = "yourtutor"
    postgres_host: str = "127.0.0.1"  # not "localhost": ::1 can stall 30 s per connection
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
    guest_start_limit_ip: int = 20  # guest starts per IP per rate window
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
    app_env: str = "development"  # env: APP_ENV; "production" blocks authoring tools
    public_web_url: str = "http://localhost:3000/guardian"  # env: PUBLIC_WEB_URL (report links)
    ask_enabled: bool = False  # env: ASK_ENABLED; Study Mode Ask is off until turned on
    ask_guests_enabled: bool = False  # env: ASK_GUESTS_ENABLED; guests never get Ask by default
    llm_api_key: str = ""  # env: LLM_API_KEY; no key means no LLM calls
    llm_model_fast: str = ""  # env: LLM_MODEL_FAST (hints, encouragement)
    llm_model_strong: str = ""  # env: LLM_MODEL_STRONG (explain-back grading, explanations)
    llm_review_sample_rate: float = 1.0  # env: LLM_REVIEW_SAMPLE_RATE; 100% in the first pilot week
    cors_extra_origins: str = ""  # env: CORS_EXTRA_ORIGINS, comma separated (LAN preview)


settings = Settings()
