from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_JWT_SECRET = "dev_only_jwt_secret_change_me_before_deploying_0001"


class Settings(BaseSettings):
    # Ambiente e Identidade do Projeto
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    PROJECT_NAME: str = "QUERO - Quadro Universitário de Estágios Remunerados e Oportunidades"
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "America/Sao_Paulo"
    API_DOCS_ENABLED: bool = True

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_dev_secret_change_me"
    POSTGRES_DB: str = "quero_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    SQL_ECHO: bool = False

    # Segurança e JWT
    JWT_SECRET_KEY: str = DEFAULT_DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    # Senha atribuída na inicialização a usuários já cadastrados que ainda não possuem senha
    # (ex.: contas criadas pela migração de carga inicial). Deixe vazio para não alterar nada.
    INITIAL_USERS_PASSWORD: Optional[str] = None
    # Permite que estudantes criem a própria conta pela tela de cadastro.
    ALLOW_STUDENT_SIGNUP: bool = True

    # Armazenamento de Arquivos: "database" (persistente no PostgreSQL) ou "local" (disco)
    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "./data/documentos"
    MAX_UPLOAD_SIZE_BYTES: int = 10485760  # 10 MB

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    CORS_ORIGIN_REGEX: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def validate_for_runtime(self) -> None:
        """Impede a inicialização em produção com configurações inseguras."""
        if not self.is_production:
            return
        if self.JWT_SECRET_KEY == DEFAULT_DEV_JWT_SECRET or len(self.JWT_SECRET_KEY) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY ausente ou fraca em produção. Defina uma chave aleatória com ao menos 32 caracteres."
            )
        if self.STORAGE_BACKEND not in ("database", "local"):
            raise RuntimeError("STORAGE_BACKEND deve ser 'database' ou 'local'.")


settings = Settings()
settings.DATABASE_URL = settings.get_database_url()
settings.validate_for_runtime()
