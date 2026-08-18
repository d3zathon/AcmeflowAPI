"""
AcmeFlow API - configuration.

Reads settings from environment variables / .env. Defaults are deliberately
"lab-friendly" (e.g. a static SECRET_KEY) so the environment is reproducible
out of the box -- do NOT reuse these defaults outside of this local lab.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AcmeFlow API"
    DATABASE_URL: str = "postgresql://acmeflow:acmeflow@db:5432/acmeflow"
    SECRET_KEY: str = "lab-only-insecure-static-secret-do-not-reuse"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
