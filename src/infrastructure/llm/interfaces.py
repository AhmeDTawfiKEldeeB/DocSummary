from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List


class BaseLLM(ABC):
    """Abstract interface for text generation models (ISP & DIP)."""

    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes a full non-streaming generation request."""
        pass

    @abstractmethod
    async def stream(
        self, messages: List[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Executes a streaming generation request yielding token chunks."""
        pass
