from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DATABASE_URL: str | None = Field(default=None)

    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            "postgresql+asyncpg://"
            f"{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
        )


settings = Settings()
