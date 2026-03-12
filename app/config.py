from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", validate_default=False, extra="ignore"
    )

    APP_ENV: str = "development"

    # JWT
    SECRET_KEY: str
    DATABASE_URL: str
    POSTGRES_DB: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str


settings = Settings()
