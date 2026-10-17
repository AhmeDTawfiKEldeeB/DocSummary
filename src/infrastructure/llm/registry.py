from typing import Any, Dict, Optional

try:
    from src.config.settings import Settings, get_settings
    from src.infrastructure.llm.interfaces import BaseLLM
    from src.infrastructure.llm.providers import (
        GroqProvider,
        OpenAIProvider,
        VLLMProvider,
    )
except ModuleNotFoundError:
    from config.settings import Settings, get_settings
    from infrastructure.llm.interfaces import BaseLLM
    from infrastructure.llm.providers import (
        GroqProvider,
        OpenAIProvider,
        VLLMProvider,
    )


class LLMRegistry:
    """Central registry and factory for initialized generation providers."""

    def __init__(self) -> None:
        self._llms: Dict[str, BaseLLM] = {}

    def register_llm(self, key: str, provider: BaseLLM) -> None:
        self._llms[key] = provider

    def get_llm(self, key: str) -> BaseLLM:
        if key not in self._llms:
            raise KeyError(
                f"LLM Provider '{key}' is not initialized. Available: {list(self._llms.keys())}"
            )
        return self._llms[key]


# Global Registry Instance
registry = LLMRegistry()


def initialize_providers(cfg: Optional[Settings] = None) -> None:
    """Reads configuration settings and instantiates configured generation providers once."""
    config = cfg or get_settings()

    # 1. Register vLLM (Generation)
    if config.vllm_base_url:
        registry.register_llm(
            "vllm",
            VLLMProvider(
                base_url=config.vllm_base_url,
                model_name=config.vllm_model_name,
                api_key=config.vllm_api_key,
            ),
        )

    # 2. Register OpenAI (Generation)
    if config.openai_api_key:
        registry.register_llm(
            "openai",
            OpenAIProvider(
                api_key=config.openai_api_key,
                model_name=config.openai_model_name,
                base_url=config.openai_base_url,
            ),
        )

    # 3. Register Groq (Generation)
    if config.groq_api_key:
        registry.register_llm(
            "groq",
            GroqProvider(
                api_key=config.groq_api_key,
                model_name=config.groq_model_name,
                base_url=config.groq_base_url,
            ),
        )


# Trigger initialization upon module import
initialize_providers()
