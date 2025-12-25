"""Application configuration management."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # PostgreSQL
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="stockrags", alias="POSTGRES_DB")
    postgres_user: str = Field(default="stockrags", alias="POSTGRES_USER")
    postgres_password: str = Field(default="secret", alias="POSTGRES_PASSWORD")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="secret", alias="NEO4J_PASSWORD")

    # Qdrant
    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")

    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/1", alias="CELERY_BROKER_URL")

    # LLM - Cloud Providers
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    default_openai_model: str = Field(default="gpt-4o", alias="DEFAULT_OPENAI_MODEL")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    default_anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", alias="DEFAULT_ANTHROPIC_MODEL"
    )
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    default_gemini_model: str = Field(default="gemini-2.0-flash-exp", alias="DEFAULT_GEMINI_MODEL")

    # LLM - Local Providers
    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL"
    )
    default_ollama_model: str = Field(default="llama3.1:70b", alias="DEFAULT_OLLAMA_MODEL")
    lmstudio_base_url: str = Field(
        default="http://host.docker.internal:1234/v1", alias="LMSTUDIO_BASE_URL"
    )
    default_lmstudio_model: str = Field(default="local-model", alias="DEFAULT_LMSTUDIO_MODEL")
    vllm_base_url: str = Field(
        default="http://host.docker.internal:8080", alias="VLLM_BASE_URL"
    )

    # Embedding
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
