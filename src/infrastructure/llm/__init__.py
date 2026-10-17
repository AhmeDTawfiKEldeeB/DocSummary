from typing import Optional

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
    from src.infrastructure.llm.registry import registry
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM
    from infrastructure.llm.registry import registry


def get_llm(name: Optional[str] = None) -> BaseLLM:
    """Retrieves a pre-initialized generation provider instance by name (defaults to settings.default_llm_provider)."""
    provider_name = name or settings.default_llm_provider
    return registry.get_llm(provider_name)


__all__ = ["get_llm", "BaseLLM"]
