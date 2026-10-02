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


settings = Settings()
