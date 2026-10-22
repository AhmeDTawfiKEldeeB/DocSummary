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
        reasoning_effort: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "groq_api_key", "EMPTY")
        self.model_name = model_name or getattr(settings, "groq_model_name", "qwen/qwen3.8-27b")
        self.base_url = base_url or getattr(settings, "groq_base_url", "https://api.groq.com/openai/v1")
        self.max_tokens = max_tokens or getattr(settings, "groq_max_tokens", 800)
        self.reasoning_effort = (
            reasoning_effort
            if reasoning_effort is not None
            else getattr(settings, "groq_reasoning_effort", "none")
        )

    def _get_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=8,
            timeout=120.0,
        )

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    def _prepare_request_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Configures Groq-specific parameters, such as disabling reasoning/thinking."""
        call_kwargs = dict(kwargs)
        # Strip thinking_budget if present from other providers
        call_kwargs.pop("thinking_budget", None)

        reasoning_effort = call_kwargs.pop("reasoning_effort", self.reasoning_effort)
        extra_body = dict(call_kwargs.pop("extra_body", {}))

        if reasoning_effort == "none":
            if "gpt-oss" in self.model_name:
                call_kwargs["reasoning_effort"] = "low"
                extra_body.setdefault("reasoning_format", "hidden")
            else:
                call_kwargs["reasoning_effort"] = "none"
                extra_body.setdefault("reasoning_format", "hidden")
        elif reasoning_effort:
            call_kwargs["reasoning_effort"] = reasoning_effort

        if extra_body:
            call_kwargs["extra_body"] = extra_body

        return call_kwargs

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request with auto-continuation if length limit hit."""
        client = self._get_client()
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        call_kwargs = self._prepare_request_kwargs(kwargs)

        try:
            full_text = ""
            current_messages = list(messages)
            max_continuations = 3

            for _ in range(max_continuations):
                res = await client.chat.completions.create(
                    model=self.model_name,
                    messages=current_messages,
                    max_tokens=max_tokens,
                    **call_kwargs,
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
        call_kwargs = self._prepare_request_kwargs(kwargs)

        try:
            current_messages = list(messages)
            max_continuations = 3

            for _ in range(max_continuations):
                response_stream = await client.chat.completions.create(
                    model=self.model_name,
                    messages=current_messages,
                    stream=True,
                    max_tokens=max_tokens,
                    **call_kwargs,
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
