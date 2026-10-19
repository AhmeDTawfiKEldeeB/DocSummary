from typing import Any, AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM


class VLLMProvider(BaseLLM):
    """Adapter for self-hosted vLLM engine via OpenAI-compatible API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or settings.vllm_base_url or ""
        self.model_name = model_name or settings.vllm_model_name
        self.api_key = api_key or settings.vllm_api_key or "EMPTY"

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request."""
        client = self._get_client()
        try:
            res = await client.chat.completions.create(
                model=self.model_name, messages=messages, **kwargs
            )
            return res.choices[0].message.content or ""
        finally:
            await client.close()

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks."""
        client = self._get_client()
        try:
            response_stream = await client.chat.completions.create(
                model=self.model_name, messages=messages, stream=True, **kwargs
            )
            async for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        finally:
            await client.close()
