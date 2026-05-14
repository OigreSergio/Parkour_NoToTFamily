from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    cors_origins: list[str] = Field(default_factory=list)

    s3_endpoint: str | None = None
    s3_bucket: str = "parkour-spots"
    s3_region: str = "eu-west-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    initial_admin_email: str | None = None
    initial_admin_password: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("jwt_secret")
    @classmethod
    def reject_default_secret_in_prod(cls, v: str, info) -> str:
        env = info.data.get("env")
        if env == "production" and v in {"change-me-in-prod", "test-secret-not-used-in-prod", ""}:
            raise ValueError("JWT_SECRET must be set to a strong value in production")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
