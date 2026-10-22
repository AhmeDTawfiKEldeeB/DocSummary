from pathlib import Path
from typing import Optional, Union
import pymupdf
from src.services.prompts import SHORT_SUMMARY_PROMPT
try:
    from src.config.settings import settings
    from src.infrastructure.llm import get_llm
except ModuleNotFoundError:
    from config.settings import settings
    from infrastructure.llm import get_llm


class SimpleSummarizer:
    """
    Summarization pipeline for small documents (total_pages <= 15).
    Extracts text and performs direct generation via the LLM gateway using PyMuPDF.
    """

    def __init__(self, provider_name: Optional[str] = None) -> None:
        self.provider_name = provider_name or getattr(settings, "default_llm_provider", "vllm")

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """Extracts text content from a PDF file using PyMuPDF."""
        doc = pymupdf.open(str(file_path))
        text_parts = []
        try:
            for page in doc:
                text = page.get_text() or ""
                if text.strip():
                    text_parts.append(text.strip())
        finally:
            doc.close()
        return "\n\n".join(text_parts)

    async def summarize(self, file_path: Union[str, Path], **kwargs) -> str:
        """Generates a summary for a small document."""
        text = self.extract_text(file_path)
        if not text.strip():
            raise ValueError("No extractable text found in the PDF document.")

        llm = get_llm(self.provider_name)
        messages = [
            {
                "role": "system",
                "content": SHORT_SUMMARY_PROMPT,
            },
            {
                "role": "user",
                "content": text,
            },
        ]
        return await llm.generate(messages=messages, thinking_budget=0,**kwargs)
