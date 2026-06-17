from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="EDGEEYE_")

    app_name: str = "EdgeEye API"
    app_version: str = "0.1.0"
    database_path: str = "data/edgeeye.db"
    uploads_dir: str = "uploads"
    reports_dir: str = "reports"
    llm_provider: str = "rule-template"
    llm_api_url: str | None = None
    llm_api_key: str | None = None
    llm_model_name: str = "rule-template"
    llm_timeout_seconds: float = 10.0
    llm_max_retries: int = 2
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


settings = Settings()
