from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GoingOnce"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./goingonce.db"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
