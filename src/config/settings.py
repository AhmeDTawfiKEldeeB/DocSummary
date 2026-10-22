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
        default="groq", description="Default generation provider name (e.g., vllm, gemini, groq)"
    )
    default_max_tokens: int = Field(
        default=4096, description="Global default maximum generation tokens for LLMs"
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
    vllm_max_tokens: int = Field(
        default=8192,
        description="Maximum output generation tokens for vLLM",
    )
    vllm_context_window: int = Field(
        default=32768,
        description="Maximum context window size for vLLM input",
    )

    # Gemini Generation Provider
    gemini_api_key: Optional[str] = Field(
        default=None, description="API Key for Google Gemini cloud services"
    )
    gemini_base_url: Optional[str] = Field(
        default=None, description="Custom base URL for Gemini endpoint (optional)"
    )
    gemini_model_name: str = Field(
        default="gemini-2.5-flash", description="Default Gemini model name"
    )
    gemini_max_tokens: int = Field(
        default=8192, description="Maximum output tokens for Gemini generation"
    )
    gemini_thinking_budget: Optional[int] = Field(
        default=0,
        description="Thinking budget in tokens for Gemini models (0 = disabled, -1 = auto, >0 = token budget)",
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
        default="qwen/qwen3.8-27b", description="Default Groq generation model name"
    )
    groq_max_tokens: int = Field(
        default=800, description="Maximum output tokens for Groq models to avoid OTPM rate limits"
    )
    groq_reasoning_effort: Optional[str] = Field(
        default="none",
        description="Reasoning effort for Groq reasoning models: 'none' to disable thinking, 'low', 'medium', 'high', or None to omit",
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

    # Database Settings (PostgreSQL / Async)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        description="Async database connection URL",
    )
    database_echo: bool = Field(
        default=False, description="Enable SQLAlchemy engine query logging"
    )

    # Redis Cache & Message Broker
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Document File Storage
    storage_dir: Path = Field(
        default=BASE_DIR / "uploads",
        description="Local directory for uploaded PDF documents",
    )
    max_file_size_bytes: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum allowed PDF file size in bytes (default 50MB)",
    )

    # Celery & Worker Execution Settings
    celery_task_time_limit: int = Field(
        default=3600,
        description="Hard time limit for Celery tasks in seconds (default 1h)",
    )
    celery_task_soft_time_limit: int = Field(
        default=3300,
        description="Soft time limit for Celery tasks in seconds (default 55m)",
    )
    celery_task_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for transient worker errors",
    )
        # Long Document Summarization
    long_summary_tokenizer_name: str = Field(
        default="bernhardbrieger/Qwen3.8-27B-GPTQ-Int4",
        description="Tokenizer repository or local path used for long-document token counting",
    )
    max_tokens_per_chunk: int = Field(
        default=2200,
        ge=500,
        description="Target maximum number of tokens per chunk for long documents",
    )
    max_pages_per_chunk: int = Field(
        default=5,
        ge=1,
        description="Hard maximum number of pages per chunk for long documents",
    )
    long_summary_chunk_tokens: int = Field(
        default=2200,
        ge=500,
        description="Target maximum number of tokens per source chunk (alias for max_tokens_per_chunk)",
    )
    long_summary_reduce_input_tokens: int = Field(
        default=5000,
        ge=1000,
        description="Maximum target input tokens per reduction group",
    )
    long_summary_skip_reduction_threshold: int = Field(
        default=5000,
        ge=1000,
        description="Skip reduction stage if combined chunk summaries are below this token threshold",
    )
    long_summary_chunk_output_tokens: int = Field(
        default=600,
        ge=128,
        description="Maximum generated tokens for each chunk summary",
    )
    long_summary_reduce_output_tokens: int = Field(
        default=600,
        ge=128,
        description="Maximum generated tokens for each reduction summary",
    )
    long_summary_final_output_tokens: int = Field(
        default=2000,
        ge=128,
        description="Maximum generated tokens for the final summary",
    )
    long_summary_max_concurrency: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Maximum concurrent LLM requests during long-document summarization",
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
