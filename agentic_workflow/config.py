"""
Configuration management for the Agentic Workflow Framework.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    provider: str = "openai"
    model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3
    api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    database_url: str = Field(
        default="sqlite:///agentic_workflow.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    pool_size: int = 10
    max_overflow: int = 20


class VectorStoreSettings(BaseSettings):
    """Vector store settings."""

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    backend: str = Field(default="chroma", alias="VECTOR_STORE_TYPE")
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    collection_name: str = "agent_memory"
    embedding_dimension: int = 1536
    pinecone_api_key: str | None = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_index: str | None = Field(default=None, alias="PINECONE_INDEX")


class APISettings(BaseSettings):
    """API server settings."""

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8080, alias="API_PORT")
    debug: bool = Field(default=False, alias="API_DEBUG")
    secret_key: str = Field(
        default="change-me-in-production",
        alias="SECRET_KEY",
    )
    cors_origins: list[str] = ["*"]
    workers: int = 4


class ObservabilitySettings(BaseSettings):
    """Observability settings."""

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_tracing: bool = Field(default=True, alias="ENABLE_TRACING")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    log_format: str = "json"


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Agentic Workflow Framework"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Sub-settings (populated programmatically)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    api: APISettings = Field(default_factory=APISettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # Agent settings
    agent_max_iterations: int = 10
    agent_max_execution_time: int = 300

    # Workflow settings
    workflow_max_parallel_tasks: int = 5
    workflow_retry_max_attempts: int = 3

    @classmethod
    def from_yaml(cls, path: str) -> Settings:
        """Load settings from a YAML configuration file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        flat: dict[str, Any] = {}
        if "app" in data:
            flat["app_name"] = data["app"].get("name", cls.model_fields["app_name"].default)
        if "agents" in data:
            flat["agent_max_iterations"] = data["agents"].get("max_iterations", 10)
            flat["agent_max_execution_time"] = data["agents"].get("max_execution_time", 300)
        if "workflows" in data:
            flat["workflow_max_parallel_tasks"] = data["workflows"].get("max_parallel_tasks", 5)

        return cls(**flat)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    config_path = os.environ.get("CONFIG_PATH", "configs/default.yaml")
    if os.path.exists(config_path):
        return Settings.from_yaml(config_path)
    return Settings()
