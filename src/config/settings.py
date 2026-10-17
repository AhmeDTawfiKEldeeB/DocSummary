import os
from pathlib import Path
import sys
from typing import Any, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate project root and .env path reliably regardless of working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

# Ensure project root and src directory are in sys.path
for path_str in (str(BASE_DIR), str(BASE_DIR / "src")):
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class Settings(BaseSettings):
    """Application configuration loaded from .env file and environment variables with fallback defaults."""

    # Application settings
    app_name: str = Field(default="DocSummary", description="Name of the application")
    app_env: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    api_version: str = Field(default="v1", description="API version string")
    api_prefix: str = Field(default="/api/v1", description="Base API route prefix")
    host: str = Field(default="0.0.0.0", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")

    # Gateway Default Provider Selection
    default_llm_provider: str = Field(
        default="vllm", description="Default generation provider name (e.g., vllm, openai, groq)"
    )

    # vLLM Generation Provider
    vllm_base_url: Optional[str] = Field(
        default=None, description="Base URL for self-hosted vLLM instance"
    )
    vllm_api_key: str = Field(
        default="EMPTY", description="API key for vLLM instance"
    )
    vllm_model_name: str = Field(
        default="bernhardbrieger/Qwen3.8-27B-GPTQ-Int4",
        description="Model name/identifier for vLLM",
    )

    # OpenAI Generation Provider
    openai_api_key: Optional[str] = Field(
        default=None, description="API Key for OpenAI cloud services"
    )
    openai_base_url: Optional[str] = Field(
        default=None, description="Custom base URL for OpenAI endpoint (optional)"
    )
    openai_model_name: str = Field(
        default="gpt-4o-mini", description="Default OpenAI model name"
    )

    # Groq Generation Provider
    groq_api_key: Optional[str] = Field(
        default=None, description="API Key for Groq cloud services"
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Base URL for Groq API endpoint",
    )
    groq_model_name: str = Field(
        default="llama-3.3-70b-versatile", description="Default Groq generation model name"
    )

    # Vector Database Settings
    qdrant_url: Optional[str] = Field(
        default=None, description="Qdrant vector database URL"
    )
    qdrant_api_key: Optional[str] = Field(
        default=None, description="Qdrant API key"
    )
    qdrant_collection_name: str = Field(
        default="documents", description="Default collection name in Qdrant"
    )

    @model_validator(mode="before")
    @classmethod
    def strip_and_clean_empty_values(cls, values: Any) -> Any:
        """
        If a variable exists in .env or environment but is empty or only whitespace,
        strip it out so Pydantic uses the default value defined in Settings.
        """
        if not isinstance(values, dict):
            return values
        cleaned = {}
        for key, val in values.items():
            if isinstance(val, str) and val.strip() == "":
                # Ignore empty string so the field's default or None applies
                continue
            cleaned[key] = val
        return cleaned

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Returns a Settings instance loaded from .env and environment."""
    return Settings()


def reload_settings() -> Settings:
    """Reloads settings from disk/.env and updates the module-level singleton."""
    global settings
    settings = Settings()
    return settings


settings: Settings = get_settings()
