"""Application configuration using Pydantic Settings.

Loads configuration from environment variables and .env files with
proper validation and type conversion. All settings are organized
by concern (database, redis, qdrant, etc.).

Usage:
    from app.config import settings
    db_url = settings.database_url
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration.

    Attributes:
        host: Database server hostname.
        port: Database server port.
        user: Database username.
        password: Database password (must be strong in production).
        db: Database name.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections beyond pool_size.
        pool_timeout: Seconds to wait for a connection from the pool.
        pool_recycle: Seconds before recycling a connection.
        echo: Whether to log SQL statements.
    """

    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT", ge=1, le=65535)
    user: str = Field(default="rag_user", alias="POSTGRES_USER")
    password: str = Field(default="", alias="POSTGRES_PASSWORD")
    db: str = Field(default="rag_kb", alias="POSTGRES_DB")
    pool_size: int = Field(default=20, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=50)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    pool_recycle: int = Field(default=1800, ge=60, le=7200)
    echo: bool = False

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    @property
    def url(self) -> str:
        """Build async PostgreSQL connection URL.

        Returns:
            Async PostgreSQL connection string for SQLAlchemy.
        """
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_url(self) -> str:
        """Build sync PostgreSQL connection URL for Alembic.

        Returns:
            Sync PostgreSQL connection string.
        """
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration.

    Attributes:
        host: Redis server hostname.
        port: Redis server port.
        password: Redis password (empty for no auth).
        db: Redis database number.
    """

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT", ge=1, le=65535)
    password: str = Field(default="", alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB", ge=0, le=15)

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    @property
    def url(self) -> str:
        """Build Redis connection URL.

        Returns:
            Redis connection string.
        """
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration.

    Attributes:
        host: Qdrant server hostname.
        port: Qdrant HTTP API port.
        grpc_port: Qdrant gRPC port.
        collection: Default collection name for document vectors.
        api_key: Optional API key for authentication.
    """

    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT", ge=1, le=65535)
    grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT", ge=1, le=65535)
    collection: str = Field(default="rag_documents", alias="QDRANT_COLLECTION")
    api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    model_config = SettingsConfigDict(env_prefix="QDRANT_")


class JWTSettings(BaseSettings):
    """JWT authentication configuration.

    Attributes:
        secret_key: Secret key for signing JWT tokens.
        algorithm: JWT signing algorithm.
        access_token_expire_minutes: Access token TTL in minutes.
        refresh_token_expire_days: Refresh token TTL in days.
    """

    secret_key: str = Field(
        default="CHANGE_ME_in_production",
        alias="JWT_SECRET_KEY",
        min_length=16,
    )
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", ge=1, le=1440
    )
    refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS", ge=1, le=30
    )

    model_config = SettingsConfigDict(env_prefix="JWT_")


class CelerySettings(BaseSettings):
    """Celery task queue configuration.

    Attributes:
        broker_url: Celery broker URL (Redis).
        result_backend: Celery result backend URL (Redis).
    """

    broker_url: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_BROKER_URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    model_config = SettingsConfigDict(env_prefix="CELERY_")


class LLMSettings(BaseSettings):
    """LLM provider configuration (Anthropic-compatible endpoint).

    Attributes:
        base_url: LLM API base URL.
        api_key: LLM API key.
        model: Model identifier.
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature.
        stream: Whether to use streaming by default.
    """

    base_url: str = Field(
        default="https://api.xiaomimimo.com/anthropic", alias="LLM_BASE_URL"
    )
    api_key: str = Field(default="", alias="LLM_API_KEY")
    model: str = Field(default="mimo-v2-pro", alias="LLM_MODEL")
    max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS", ge=1, le=32768)
    temperature: float = Field(
        default=0.1, alias="LLM_TEMPERATURE", ge=0.0, le=2.0
    )
    stream: bool = Field(default=True, alias="LLM_STREAM")

    model_config = SettingsConfigDict(env_prefix="LLM_")


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration (BAAI/bge-m3).

    Attributes:
        model_name: HuggingFace model identifier.
        device: Device to run the model on (cpu/cuda).
        batch_size: Batch size for encoding.
        max_length: Maximum token length for embedding.
    """

    model_name: str = Field(
        default="BAAI/bge-m3", alias="EMBEDDING_MODEL_NAME"
    )
    device: str = Field(default="cpu", alias="EMBEDDING_DEVICE")
    batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE", ge=1, le=256)
    max_length: int = Field(
        default=8192, alias="EMBEDDING_MAX_LENGTH", ge=128, le=32768
    )

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")


class RerankerSettings(BaseSettings):
    """Reranker model configuration (BAAI/bge-reranker-v2-m3).

    Attributes:
        model_name: HuggingFace model identifier.
        device: Device to run the model on (cpu/cuda).
        batch_size: Batch size for scoring.
        max_length: Maximum token length for reranking.
    """

    model_name: str = Field(
        default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL_NAME"
    )
    device: str = Field(default="cpu", alias="RERANKER_DEVICE")
    batch_size: int = Field(default=32, alias="RERANKER_BATCH_SIZE", ge=1, le=256)
    max_length: int = Field(
        default=8192, alias="RERANKER_MAX_LENGTH", ge=128, le=32768
    )

    model_config = SettingsConfigDict(env_prefix="RERANKER_")


class StorageSettings(BaseSettings):
    """File storage configuration.

    Attributes:
        upload_dir: Directory for uploaded files.
        max_file_size_mb: Maximum file size in MB.
        allowed_extensions: Allowed file extensions.
    """

    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(
        default=50, alias="MAX_FILE_SIZE_MB", ge=1, le=500
    )
    allowed_extensions: str = Field(
        default=".pdf,.docx,.doc,.md,.txt,.pptx,.ppt",
        alias="ALLOWED_EXTENSIONS",
    )

    model_config = SettingsConfigDict()

    @property
    def allowed_extension_list(self) -> list[str]:
        """Parse allowed extensions into a list.

        Returns:
            List of allowed file extensions (with leading dot).
        """
        return [
            ext.strip().lower()
            for ext in self.allowed_extensions.split(",")
            if ext.strip()
        ]

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes.

        Returns:
            Maximum file size in bytes.
        """
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Get upload directory as Path object.

        Returns:
            Path to the upload directory.
        """
        return Path(self.upload_dir)


class Settings(BaseSettings):
    """Root application settings.

    Aggregates all sub-settings and provides top-level configuration.
    Environment variables are loaded from .env file if present.

    Attributes:
        app_name: Application display name.
        app_env: Environment (development/staging/production).
        debug: Enable debug mode.
        log_level: Logging level.
        cors_origins: Allowed CORS origins (comma-separated).
        db: Database settings.
        redis: Redis settings.
        qdrant: Qdrant settings.
        jwt: JWT settings.
        celery: Celery settings.
        llm: LLM settings.
        embedding: Embedding model settings.
        reranker: Reranker model settings.
        storage: File storage settings.
    """

    app_name: str = Field(default="RAG-KB-System", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    # Sub-settings loaded from environment
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    reranker: RerankerSettings = Field(default_factory=RerankerSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment.

        Args:
            v: Environment name.

        Returns:
            Validated environment name.

        Raises:
            ValueError: If environment is not valid.
        """
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level.

        Args:
            v: Log level string.

        Returns:
            Validated log level (uppercase).

        Raises:
            ValueError: If log level is not valid.
        """
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production mode.

        Returns:
            True if app_env is 'production'.
        """
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode.

        Returns:
            True if app_env is 'development'.
        """
        return self.app_env == "development"

    @property
    def database_url(self) -> str:
        """Get async database URL.

        Returns:
            Async PostgreSQL connection string.
        """
        return self.db.url

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins into a list.

        Returns:
            List of allowed CORS origins.
        """
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings singleton.

    Returns:
        Cached Settings instance.
    """
    return Settings()


# Module-level settings singleton
settings = get_settings()
