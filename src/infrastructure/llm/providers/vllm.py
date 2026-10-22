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
        """
        Executes a full generation request by streaming tokens over the wire.
        This keeps the HTTP connection continuously active, preventing ngrok/proxy 503/524 timeouts.
        """
        full_text: List[str] = []
        async for token in self.stream(messages, **kwargs):
            full_text.append(token)
        return "".join(full_text).strip()

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request with automatic continuation if max_tokens is reached."""
        client = self._get_client()
        params = self._build_params(kwargs)
        max_tokens_budget = params.get("max_tokens")
        logger.debug(
            "vLLM stream starting: model=%s, max_tokens=%s, temperature=%s",
            self.model_name,
            max_tokens_budget,
            params.get("temperature"),
        )
        try:
            current_messages = list(messages)
            max_continuations = 3
            finish_reason = None

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
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                    content = getattr(choice.delta, "content", None)
                    if content:
                        accumulated += content
                        yield content

                if finish_reason != "length":
                    break

                if attempt < max_continuations - 1:
                    logger.warning(
                        "Stream hit max_tokens limit (%s); automatically continuing stream (attempt %d/%d)...",
                        max_tokens_budget,
                        attempt + 1,
                        max_continuations,
                    )
                    current_messages.append({"role": "assistant", "content": accumulated})
                    current_messages.append({
                        "role": "user",
                        "content": "Please continue writing the remaining content and provide the complete final conclusion.",
                    })
                else:
                    logger.warning(
                        "Stream reached max continuations (%d) and output remains truncated at max_tokens=%s. Appending truncation notice.",
                        max_continuations,
                        max_tokens_budget,
                    )
                    yield TRUNCATION_NOTE
        finally:
            await client.close()