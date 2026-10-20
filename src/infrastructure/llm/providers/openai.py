from typing import Any, AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM


class OpenAIProvider(BaseLLM):
    """Adapter for OpenAI cloud generation models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or settings.openai_api_key or "EMPTY"
        self.model_name = model_name or settings.openai_model_name
        self.base_url = base_url or settings.openai_base_url
        self.max_tokens = max_tokens or getattr(settings, "openai_max_tokens", getattr(settings, "default_max_tokens", 4096))

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request."""
        client = self._get_client()
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        try:
            res = await client.chat.completions.create(
                model=self.model_name, messages=messages, max_tokens=max_tokens, **kwargs
            )
            return res.choices[0].message.content or ""
        finally:
            await client.close()

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks."""
        client = self._get_client()
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        try:
            response_stream = await client.chat.completions.create(
                model=self.model_name, messages=messages, stream=True, max_tokens=max_tokens, **kwargs
            )
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        finally:
            await client.close()
