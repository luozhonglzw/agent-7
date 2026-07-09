"""Configuration module unit tests.

Tests for Pydantic Settings validation and computed properties.
"""

import pytest
from pydantic import ValidationError

from app.config import (
    DatabaseSettings,
    RedisSettings,
    QdrantSettings,
    JWTSettings,
    LLMSettings,
    EmbeddingSettings,
    StorageSettings,
)


class TestDatabaseSettings:
    """Tests for database configuration."""

    def test_default_values(self) -> None:
        """Test default database settings."""
        db = DatabaseSettings()

        assert db.host == "localhost"
        assert db.port == 5432
        assert db.user == "rag_user"
        assert db.db == "rag_kb"
        assert db.pool_size == 20

    def test_url_property(self) -> None:
        """Test async URL generation."""
        db = DatabaseSettings(
            POSTGRES_HOST="db.example.com",
            POSTGRES_PORT=5433,
            POSTGRES_USER="myuser",
            POSTGRES_PASSWORD="mypass",
            POSTGRES_DB="mydb",
        )

        url = db.url
        assert "postgresql+asyncpg://" in url
        assert "myuser:mypass" in url
        assert "db.example.com:5433" in url
        assert "mydb" in url

    def test_invalid_port(self) -> None:
        """Test validation of invalid port."""
        with pytest.raises(ValidationError):
            DatabaseSettings(POSTGRES_PORT=99999)

    def test_sync_url_property(self) -> None:
        """Test sync URL generation for Alembic."""
        db = DatabaseSettings()
        url = db.sync_url

        assert "postgresql+psycopg2://" in url


class TestRedisSettings:
    """Tests for Redis configuration."""

    def test_default_values(self) -> None:
        """Test default Redis settings."""
        redis = RedisSettings()

        assert redis.host == "localhost"
        assert redis.port == 6379
        assert redis.db == 0

    def test_url_without_password(self) -> None:
        """Test URL generation without password."""
        redis = RedisSettings(REDIS_HOST="redis.local", REDIS_PORT=6380)

        url = redis.url
        assert "redis://" in url
        assert "redis.local:6380" in url
        assert ":" not in url.split("@")[0]  # No password in URL

    def test_url_with_password(self) -> None:
        """Test URL generation with password."""
        redis = RedisSettings(
            REDIS_HOST="redis.local",
            REDIS_PASSWORD="secret",
        )

        url = redis.url
        assert ":secret@" in url


class TestJWTSettings:
    """Tests for JWT configuration."""

    def test_default_values(self) -> None:
        """Test default JWT settings."""
        jwt = JWTSettings(JWT_SECRET_KEY="my_secret_key_that_is_long_enough")

        assert jwt.algorithm == "HS256"
        assert jwt.access_token_expire_minutes == 15
        assert jwt.refresh_token_expire_days == 7

    def test_short_secret_key_raises_error(self) -> None:
        """Test validation of short secret key."""
        with pytest.raises(ValidationError):
            JWTSettings(JWT_SECRET_KEY="short")


class TestLLMSettings:
    """Tests for LLM configuration."""

    def test_default_values(self) -> None:
        """Test default LLM settings."""
        llm = LLMSettings()

        assert llm.base_url == "https://api.xiaomimimo.com/anthropic"
        assert llm.model == "mimo-v2-pro"
        assert llm.max_tokens == 4096
        assert llm.temperature == 0.1
        assert llm.stream is True

    def test_invalid_temperature(self) -> None:
        """Test validation of invalid temperature."""
        with pytest.raises(ValidationError):
            LLMSettings(LLM_TEMPERATURE=3.0)


class TestEmbeddingSettings:
    """Tests for embedding configuration."""

    def test_default_values(self) -> None:
        """Test default embedding settings."""
        emb = EmbeddingSettings()

        assert emb.model_name == "BAAI/bge-m3"
        assert emb.device == "cpu"
        assert emb.batch_size == 32
        assert emb.max_length == 8192


class TestStorageSettings:
    """Tests for storage configuration."""

    def test_allowed_extension_list(self) -> None:
        """Test extension list parsing."""
        storage = StorageSettings(
            ALLOWED_EXTENSIONS=".pdf,.docx,.md,.txt"
        )

        ext_list = storage.allowed_extension_list
        assert ".pdf" in ext_list
        assert ".docx" in ext_list
        assert ".md" in ext_list
        assert ".txt" in ext_list

    def test_max_file_size_bytes(self) -> None:
        """Test file size conversion."""
        storage = StorageSettings(MAX_FILE_SIZE_MB=100)

        assert storage.max_file_size_bytes == 100 * 1024 * 1024

    def test_upload_path_property(self) -> None:
        """Test upload path as Path object."""
        storage = StorageSettings(UPLOAD_DIR="./test_uploads")

        from pathlib import Path
        assert isinstance(storage.upload_path, Path)
