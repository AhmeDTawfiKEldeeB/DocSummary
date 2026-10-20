from typing import Any, AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM


class GroqProvider(BaseLLM):
    """Adapter for Groq cloud generation models via OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or settings.groq_api_key or "EMPTY"
        self.model_name = model_name or settings.groq_model_name
        self.base_url = base_url or settings.groq_base_url
        self.max_tokens = max_tokens or getattr(settings, "groq_max_tokens", 800)

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request with auto-continuation if length limit hit."""
        client = self._get_client()
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        try:
            full_text = ""
            current_messages = list(messages)
            max_continuations = 3

            for _ in range(max_continuations):
                res = await client.chat.completions.create(
                    model=self.model_name, messages=current_messages, max_tokens=max_tokens, **kwargs
                )
                choice = res.choices[0]
                chunk_text = choice.message.content or ""
                full_text = f"{full_text} {chunk_text}".strip() if full_text else chunk_text

                if choice.finish_reason != "length":
                    break

                current_messages.append({"role": "assistant", "content": chunk_text})
                current_messages.append({
                    "role": "user",
                    "content": "Please continue writing the remaining content and provide the complete final conclusion.",
                })

            return full_text
        finally:
            await client.close()

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks with auto-continuation if length limit hit."""
        client = self._get_client()
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        try:
            current_messages = list(messages)
            max_continuations = 3

            for _ in range(max_continuations):
                response_stream = await client.chat.completions.create(
                    model=self.model_name, messages=current_messages, stream=True, max_tokens=max_tokens, **kwargs
                )
                accumulated = ""
                finish_reason = None

                async for chunk in response_stream:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    finish_reason = choice.finish_reason
                    if choice.delta.content:
                        accumulated += choice.delta.content
                        yield choice.delta.content

                if finish_reason != "length":
                    break

                current_messages.append({"role": "assistant", "content": accumulated})
                current_messages.append({
                    "role": "user",
                    "content": "Please continue writing the remaining content and provide the complete final conclusion.",
                })
        finally:
            await client.close()
