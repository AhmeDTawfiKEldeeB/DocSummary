try:
    from src.services.prompts.prompts import (
        LONG_CHUNK_SUMMARY_PROMPT,
        LONG_FINAL_SUMMARY_PROMPT,
        LONG_REDUCTION_PROMPT,
        SHORT_SUMMARY_PROMPT,
    )
except (ModuleNotFoundError, ImportError):
    from services.prompts.prompts import (
        LONG_CHUNK_SUMMARY_PROMPT,
        LONG_FINAL_SUMMARY_PROMPT,
        LONG_REDUCTION_PROMPT,
        SHORT_SUMMARY_PROMPT,
    )

SHORT_SUMMURY_PROMPT = SHORT_SUMMARY_PROMPT

__all__ = [
    "SHORT_SUMMARY_PROMPT",
    "SHORT_SUMMURY_PROMPT",
    "LONG_CHUNK_SUMMARY_PROMPT",
    "LONG_REDUCTION_PROMPT",
    "LONG_FINAL_SUMMARY_PROMPT",
]
