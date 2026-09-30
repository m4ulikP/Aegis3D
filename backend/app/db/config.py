from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central environment-based configuration for Aegis3D database connection."""

    POSTGRES_HOST: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="aegis3d", validation_alias="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="aegis_user", validation_alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="aegis_password", validation_alias="POSTGRES_PASSWORD")

    DATABASE_URL: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")

    DB_POOL_SIZE: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    DB_ECHO: bool = Field(default=False, validation_alias="DB_ECHO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sync_database_url(self) -> str:
        """Construct or normalize the synchronous database connection URL."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
