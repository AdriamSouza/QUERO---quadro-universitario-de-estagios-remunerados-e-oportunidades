from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Ambiente e Identidade do Projeto
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    PROJECT_NAME: str = "QUERO - Quadro Universitário de Estágios Remunerados e Oportunidades"
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_dev_secret_change_me"
    POSTGRES_DB: str = "quero_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Segurança e JWT
    JWT_SECRET_KEY: str = "super_secret_jwt_key_for_development_purposes_only_32_chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    USE_MOCK_AUTH: bool = True

    # Armazenamento de Arquivos
    STORAGE_PATH: str = "./data/documentos"
    MAX_UPLOAD_SIZE_BYTES: int = 10485760  # 10 MB

    # CORS
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
settings.DATABASE_URL = settings.get_database_url()
