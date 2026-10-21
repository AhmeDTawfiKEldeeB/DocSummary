import inspect
from typing import Any, AsyncGenerator, Dict, List, Optional
from google import genai
from google.genai import types

try:
    from src.config.settings import settings
    from src.infrastructure.llm.interfaces import BaseLLM
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm.interfaces import BaseLLM


class GeminiProvider(BaseLLM):
    """Adapter for Google Gemini generation models using the official Google GenAI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        thinking_budget: Optional[int] = None,
    ):
        self.api_key = api_key or getattr(settings, "gemini_api_key", None)
        self.model_name = model_name or getattr(settings, "gemini_model_name", "gemini-2.5-flash")
        self.base_url = base_url or getattr(settings, "gemini_base_url", None)
        self.max_tokens = max_tokens or getattr(
            settings, "gemini_max_tokens", getattr(settings, "default_max_tokens", 8192)
        )
        self.thinking_budget = (
            thinking_budget
            if thinking_budget is not None
            else getattr(settings, "gemini_thinking_budget", 0)
        )

    def _get_client(self) -> genai.Client:
        key = self.api_key or "EMPTY"
        http_options = types.HttpOptions(base_url=self.base_url) if self.base_url else None
        return genai.Client(
            api_key=key,
            http_options=http_options,
        )

    @property
    def client(self) -> genai.Client:
        return self._get_client()

    def _prepare_request(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> tuple[List[types.Content], types.GenerateContentConfig]:
        """Converts OpenAI-style messages list into Google GenAI contents and config."""
        contents: List[types.Content] = []
        system_prompts: List[str] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_prompts.append(content)
            elif role == "assistant":
                contents.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=content)],
                    )
                )
            else:  # user or any other role
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=content)],
                    )
                )

        system_instruction = "\n\n".join(system_prompts) if system_prompts else None
        max_output_tokens = kwargs.pop("max_tokens", self.max_tokens)
        temperature = kwargs.pop("temperature", None)
        thinking_budget = kwargs.pop("thinking_budget", self.thinking_budget)

        config_dict: Dict[str, Any] = {}
        if system_instruction:
            config_dict["system_instruction"] = system_instruction
        if max_output_tokens:
            config_dict["max_output_tokens"] = max_output_tokens
        if temperature is not None:
            config_dict["temperature"] = temperature

        if thinking_budget is not None:
            # ThinkingConfig is supported on Gemini 2.0 / 2.5 models (e.g. gemini-2.5-flash).
            # We omit it for legacy 1.0/1.5 models to prevent API validation errors.
            is_legacy = "1.5" in self.model_name or "1.0" in self.model_name
            if not is_legacy:
                config_dict["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)

        # Map any extra supported kwargs into GenerateContentConfig
        for k, v in list(kwargs.items()):
            if k in types.GenerateContentConfig.model_fields:
                config_dict[k] = v

        config = types.GenerateContentConfig(**config_dict)
        return contents, config

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request."""
        client = self._get_client()
        contents, config = self._prepare_request(messages, **kwargs)
        try:
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            return response.text or ""
        finally:
            await client.aio.aclose()

    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks."""
        client = self._get_client()
        contents, config = self._prepare_request(messages, **kwargs)
        try:
            stream_or_coro = client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            if inspect.isawaitable(stream_or_coro):
                response_stream = await stream_or_coro
            else:
                response_stream = stream_or_coro

            async for chunk in response_stream:
                text = chunk.text
                if text:
                    yield text
        finally:
            await client.aio.aclose()
