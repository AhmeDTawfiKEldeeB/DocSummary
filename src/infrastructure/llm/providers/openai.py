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
    ):
        self.api_key = api_key or settings.openai_api_key or "EMPTY"
        self.model_name = model_name or settings.openai_model_name
        self.base_url = base_url or settings.openai_base_url
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request."""
        res = await self.client.chat.completions.create(
            model=self.model_name, messages=messages, **kwargs
        )
        return res.choices[0].message.content or ""

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks."""
        response_stream = await self.client.chat.completions.create(
            model=self.model_name, messages=messages, stream=True, **kwargs
        )
        async for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
