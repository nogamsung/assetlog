import json
import logging
from typing import Annotated

from fastapi import Depends
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # Database
    database_url: str = "mysql+asyncmy://assetlog:assetlog@localhost:3306/assetlog"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Cookie
    cookie_secure: bool = False
    cookie_samesite: str = "strict"

    # Scheduler
    refresh_interval_minutes: int = 60
    enable_scheduler: bool = True

    # Timezone
    tz: str = "Asia/Seoul"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item) for item in v]
        return []


settings = Settings()


def get_settings() -> Settings:
    """FastAPI Depends factory — override in tests via app.dependency_overrides."""
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
