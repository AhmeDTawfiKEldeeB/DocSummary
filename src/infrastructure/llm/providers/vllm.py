import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM

logger = logging.getLogger(__name__)

TRUNCATION_NOTE = "\n\n[Warning: summary was cut off]"


class VLLMProvider(BaseLLM):
    """Adapter for self-hosted vLLM engine via OpenAI-compatible API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.base_url = base_url or settings.vllm_base_url or ""
        self.model_name = model_name or settings.vllm_model_name
        self.api_key = api_key or settings.vllm_api_key or "EMPTY"
        self.max_tokens = max_tokens or getattr(settings, "vllm_max_tokens", 4096)

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    def _build_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply shared defaults: max_tokens, low temperature, thinking off."""
        params = dict(kwargs)
        params["max_tokens"] = params.pop("max_tokens", self.max_tokens)
        params["temperature"] = params.pop("temperature", 0.2)

        extra_body = dict(params.pop("extra_body", None) or {})
        chat_kwargs = dict(extra_body.get("chat_template_kwargs") or {})
        chat_kwargs.setdefault("enable_thinking", False)
        extra_body["chat_template_kwargs"] = chat_kwargs
        params["extra_body"] = extra_body
        return params

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full generation request with automatic continuation if max_tokens is reached."""
        client = self._get_client()
        params = self._build_params(kwargs)
        try:
            full_text = ""
            current_messages = list(messages)
            max_continuations = 3

            for attempt in range(max_continuations):
                res = await client.chat.completions.create(
                    model=self.model_name, messages=current_messages, **params
                )
                choice = res.choices[0]
                chunk_text = choice.message.content or ""
                full_text = f"{full_text} {chunk_text}".strip() if full_text else chunk_text

                if choice.finish_reason != "length":
                    break

                logger.info(
                    "Generation hit max_tokens limit (%s); automatically continuing (attempt %d)...",
                    params.get("max_tokens"),
                    attempt + 1,
                )
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
        """Executes a streaming generation request with automatic continuation if max_tokens is reached."""
        client = self._get_client()
        params = self._build_params(kwargs)
        try:
            current_messages = list(messages)
            max_continuations = 3

            for attempt in range(max_continuations):
                response_stream = await client.chat.completions.create(
                    model=self.model_name, messages=current_messages, stream=True, **params
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

                logger.info(
                    "Stream hit max_tokens limit (%s); automatically continuing stream (attempt %d)...",
                    params.get("max_tokens"),
                    attempt + 1,
                )
                current_messages.append({"role": "assistant", "content": accumulated})
                current_messages.append({
                    "role": "user",
                    "content": "Please continue writing the remaining content and provide the complete final conclusion.",
                })
        finally:
            await client.close()