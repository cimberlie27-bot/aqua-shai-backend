"""
config.py
---------
Loads environment variables from .env into a typed Settings object.
Usage anywhere:  from app.config import settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- App ----
    APP_NAME: str = "VitaSip API"
    APP_ENV: str = "development"

    # ---- Database ----
    DATABASE_URL: str = "sqlite:///./water_refilling_station.db"

    # ---- Auth ----
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ---- CORS (comma-separated in .env) ----
    CORS_ORIGINS: str = "http://localhost:8100,http://127.0.0.1:8100"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS into a clean list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()