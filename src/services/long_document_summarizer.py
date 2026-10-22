import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from src.config.settings import settings
    from src.infrastructure.llm import get_llm
    from src.services.prompts import (
        LONG_CHUNK_SUMMARY_PROMPT,
        LONG_FINAL_SUMMARY_PROMPT,
        LONG_REDUCTION_PROMPT,
    )
except (ModuleNotFoundError, ImportError):
    from config.settings import settings
    from infrastructure.llm import get_llm
    from services.prompts.prompts import (
        LONG_CHUNK_SUMMARY_PROMPT,
        LONG_FINAL_SUMMARY_PROMPT,
        LONG_REDUCTION_PROMPT,
    )

logger = logging.getLogger(__name__)


@dataclass
class PageData:
    """Structured representation of an extracted PDF page."""

    page_number: int
    text: str
    token_count: int
    headings: List[str] = field(default_factory=list)
    first_heading_at_start: Optional[str] = None
    starts_near_top_table: bool = False
    first_table_cols: int = 0
    first_table_header: Optional[List[str]] = None
    ends_near_bottom_table: bool = False
    last_table_cols: int = 0
    table_continues_to_next: bool = False


@dataclass
class ChunkData:
    """A logical document chunk containing text from one or more pages."""

    chunk_index: int
    text: str
    token_count: int
    page_numbers: List[int]
    headings: List[str]
    section_header_line: str

    @property
    def page_count(self) -> int:
        return len(self.page_numbers)


def table_to_markdown(rows: List[List[Any]]) -> str:
    """Converts a 2D list of table cells into a clean Markdown table string."""
    if not rows or not rows[0]:
        return ""

    cleaned_rows: List[List[str]] = []
    for row in rows:
        cleaned_row = [
            (str(cell) if cell is not None else "").strip().replace("\n", " ")
            for cell in row
        ]
        cleaned_rows.append(cleaned_row)

    num_cols = max(len(r) for r in cleaned_rows)
    if num_cols == 0:
        return ""

    normalized_rows: List[List[str]] = []
    for r in cleaned_rows:
        if len(r) < num_cols:
            normalized_rows.append(r + [""] * (num_cols - len(r)))
        else:
            normalized_rows.append(r[:num_cols])

    header = "| " + " | ".join(normalized_rows[0]) + " |"
    separator = "| " + " | ".join(["---"] * num_cols) + " |"
    body_lines = ["| " + " | ".join(r) + " |" for r in normalized_rows[1:]]

    return "\n".join([header, separator] + body_lines)


CONNECTING_TITLE_WORDS = {
    "and", "or", "of", "in", "to", "for", "with", "on", "at", "by", "from", "the", "a", "an"
}


def is_chapter_heading(line: str) -> bool:
    """
    Checks if a line is a chapter-level heading (e.g., '6. Data and Visualization').
    Excludes subsections (e.g., '2.1'), numbered lists ending with '.',
    and Table of Contents lines containing dot leaders.
    """
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 80:
        return False
    if cleaned.endswith((".", ";", "!", "?")):
        return False
    if "..." in cleaned or "…" in cleaned or "·" in cleaned:
        return False

    # Chapter-level only: single integer followed by dot, space, and capital letter
    return bool(re.match(r"^\d+\.\s+[A-Z]", cleaned))


def detect_chapter_headings(text: str) -> List[str]:
    """
    Scans text for chapter-level headings, joining wrapped titles onto the next line
    only if the title cleanly wraps without sentence-ending punctuation or list continuation.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    headings: List[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        if is_chapter_heading(line):
            words = line.split()
            last_word = words[-1].lower().rstrip(":,")
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""

            # Check if line legitimately wraps onto next line
            if next_line and (last_word in CONNECTING_TITLE_WORDS or line.endswith((": ", "-"))):
                if next_line.endswith((".", "!", "?")):
                    # Wrapped line terminates with period -> sentence/numbered list item, not heading
                    idx += 2
                    continue
                else:
                    combined = f"{line} {next_line}".strip()
                    if len(combined) <= 120 and not combined.endswith((".", "!", "?")):
                        headings.append(combined)
                        idx += 2
                        continue

            # Skip lines that are incomplete sentences from numbered list items
            if next_line and next_line.endswith((".", "!", "?")):
                if len(line) > 50 and any(
                    w in line.lower() for w in ["using", "through", "against", "between", "during", "and", "or"]
                ):
                    idx += 1
                    continue

            headings.append(line)
        idx += 1

    return headings


class LongDocumentSummarizer:
    """
    Hierarchical map-reduce summarization pipeline for large, text-based PDFs.
    Extracts structural tables, respects chapter boundaries, and summarizes in parallel.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        chunk_output_tokens: Optional[int] = None,
        reduce_input_tokens: Optional[int] = None,
        reduce_output_tokens: Optional[int] = None,
        final_output_tokens: Optional[int] = None,
        skip_reduction_threshold: Optional[int] = None,
        max_concurrency: Optional[int] = None,
    ) -> None:
        self.provider_name = (
            provider_name
            or getattr(settings, "default_llm_provider", "vllm")
        )

        tokenizer_name = (
            getattr(settings, "long_summary_tokenizer_name", None)
            or getattr(settings, "vllm_model_name", None)
        )

        self.tokenizer = None
        if tokenizer_name:
            try:
                from transformers import AutoTokenizer

                self.tokenizer = AutoTokenizer.from_pretrained(
                    tokenizer_name,
                    use_fast=True,
                )
            except Exception as exc:
                logger.warning(
                    "Tokenizer '%s' unavailable (%s). Using heuristic token estimation.",
                    tokenizer_name,
                    exc,
                )

        # Chunker configuration
        self.max_tokens_per_chunk = int(
            getattr(settings, "max_tokens_per_chunk", 2200)
        )
        self.max_pages_per_chunk = int(
            getattr(settings, "max_pages_per_chunk", 5)
        )
        self.chunk_tokens = self.max_tokens_per_chunk

        # Overrun limits for multi-page tables
        self.max_table_overrun_pages = 8
        self.max_table_overrun_tokens = self.max_tokens_per_chunk * 2

        # Concurrency and token budgets
        self.max_concurrency = (
            max_concurrency
            if max_concurrency is not None
            else max(1, int(getattr(settings, "long_summary_max_concurrency", 6)))
        )
        self.chunk_output_tokens = (
            chunk_output_tokens
            if chunk_output_tokens is not None
            else int(getattr(settings, "long_summary_chunk_output_tokens", 600))
        )
        self.reduce_input_tokens = (
            reduce_input_tokens
            if reduce_input_tokens is not None
            else int(getattr(settings, "long_summary_reduce_input_tokens", 5000))
        )
        self.reduce_output_tokens = (
            reduce_output_tokens
            if reduce_output_tokens is not None
            else int(getattr(settings, "long_summary_reduce_output_tokens", 600))
        )
        self.final_output_tokens = (
            final_output_tokens
            if final_output_tokens is not None
            else int(getattr(settings, "long_summary_final_output_tokens", 2000))
        )
        self.skip_reduction_threshold = (
            skip_reduction_threshold
            if skip_reduction_threshold is not None
            else int(getattr(settings, "long_summary_skip_reduction_threshold", 5000))
        )

        # Confirmed server context limit (8,192 for vLLM model)
        self.server_context_limit = (
            8192
            if self.provider_name == "vllm"
            else int(getattr(settings, "vllm_context_window", 8192))
        )

    def _count_tokens(self, text: str) -> int:
        """Estimates token count using the model tokenizer or len(text) // 4 fallback."""
        if not text:
            return 0
        if self.tokenizer is not None:
            try:
                return len(self.tokenizer.encode(text, add_special_tokens=False))
            except Exception:
                pass
        return max(1, len(text) // 4)

    def _estimate_prompt_tokens(self, system_prompt: str, user_content: str) -> int:
        """Estimates total prompt tokens including system prompt and chat template overhead."""
        if self.tokenizer is not None:
            try:
                rendered = self.tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
                return len(self.tokenizer.encode(rendered, add_special_tokens=False))
            except Exception:
                pass
        return self._count_tokens(system_prompt) + self._count_tokens(user_content) + 50

    def _fallback_extract_page(
        self, file_path: Union[str, Path], page_index: int
    ) -> str:
        """Fallback per-page text extractor using pymupdf, pypdf, or placeholder."""
        try:
            import pymupdf as fitz

            with fitz.open(str(file_path)) as doc:
                if 0 <= page_index < len(doc):
                    return (doc[page_index].get_text("text") or "").strip()
        except Exception as fitz_err:
            logger.debug("PyMuPDF fallback failed on page %d: %s", page_index + 1, fitz_err)

        try:
            import pypdf

            reader = pypdf.PdfReader(str(file_path))
            if 0 <= page_index < len(reader.pages):
                return (reader.pages[page_index].extract_text() or "").strip()
        except Exception as pypdf_err:
            logger.debug("pypdf fallback failed on page %d: %s", page_index + 1, pypdf_err)

        logger.warning("All text extractors failed for page %d.", page_index + 1)
        return f"[Page {page_index + 1}: text could not be extracted]"

    def extract_pages(self, file_path: Union[str, Path]) -> List[PageData]:
        """
        Extracts document pages using pdfplumber, converting tables into Markdown
        and tracking cross-page table continuity and chapter headings.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF document not found: {path}")

        import pdfplumber

        try:
            pdf = pdfplumber.open(str(path))
        except Exception as open_err:
            err_str = str(open_err).lower()
            if "encrypt" in err_str or "password" in err_str:
                raise ValueError("PDF document is encrypted and cannot be processed.") from open_err
            raise

        with pdf:
            if getattr(pdf, "is_encrypted", False):
                raise ValueError("PDF document is encrypted and cannot be processed.")

            total_pages = len(pdf.pages)
            if total_pages == 0:
                raise ValueError("The PDF document contains 0 pages.")

            pages: List[PageData] = []

            for idx, p in enumerate(pdf.pages):
                page_num = idx + 1
                page_text_parts: List[str] = []
                starts_near_top_table = False
                first_table_cols = 0
                first_table_header = None
                ends_near_bottom_table = False
                last_table_cols = 0

                try:
                    tables = sorted(p.find_tables(), key=lambda t: t.bbox[1])
                    if tables:
                        # First table metadata
                        first_t = tables[0]
                        if first_t.bbox[1] <= p.height * 0.15:
                            starts_near_top_table = True
                            first_rows = first_t.extract() or []
                            if first_rows and first_rows[0]:
                                first_table_cols = len(first_rows[0])
                                first_table_header = [
                                    (str(c) if c is not None else "").strip()
                                    for c in first_rows[0]
                                ]

                        # Last table metadata
                        last_t = tables[-1]
                        if (p.height - last_t.bbox[3]) <= p.height * 0.10:
                            ends_near_bottom_table = True
                            last_rows = last_t.extract() or []
                            if last_rows and last_rows[0]:
                                last_table_cols = len(last_rows[0])

                        # Interleave text segments and markdown tables
                        last_bottom = 0.0
                        for t in tables:
                            top_crop = max(0.0, last_bottom)
                            bot_crop = t.bbox[1]
                            if bot_crop > top_crop:
                                seg = p.crop((0, top_crop, p.width, bot_crop)).extract_text()
                                if seg and seg.strip():
                                    page_text_parts.append(seg.strip())

                            md_table = table_to_markdown(t.extract() or [])
                            if md_table:
                                page_text_parts.append(md_table)

                            last_bottom = t.bbox[3]

                        if last_bottom < p.height:
                            seg = p.crop((0, last_bottom, p.width, p.height)).extract_text()
                            if seg and seg.strip():
                                page_text_parts.append(seg.strip())

                        page_text_raw = "\n\n".join(page_text_parts).strip()
                    else:
                        page_text_raw = (p.extract_text() or "").strip()

                except Exception as page_err:
                    logger.warning(
                        "pdfplumber extraction failed on page %d: %s. Using fallback.",
                        page_num,
                        page_err,
                    )
                    page_text_raw = self._fallback_extract_page(path, idx)

                if not page_text_raw:
                    page_text_raw = self._fallback_extract_page(path, idx)

                formatted_text = f"[Page {page_num}]\n{page_text_raw}"
                token_count = self._count_tokens(formatted_text)
                headings = detect_chapter_headings(page_text_raw)

                # Check if page begins with a chapter heading within first 3 lines
                first_heading_at_start = None
                raw_lines = [l.strip() for l in page_text_raw.split("\n") if l.strip()]
                for line in raw_lines[:3]:
                    if is_chapter_heading(line):
                        first_heading_at_start = line
                        break

                pages.append(
                    PageData(
                        page_number=page_num,
                        text=formatted_text,
                        token_count=token_count,
                        headings=headings,
                        first_heading_at_start=first_heading_at_start,
                        starts_near_top_table=starts_near_top_table,
                        first_table_cols=first_table_cols,
                        first_table_header=first_table_header,
                        ends_near_bottom_table=ends_near_bottom_table,
                        last_table_cols=last_table_cols,
                    )
                )

            # Detect table continuity between adjacent pages
            for i in range(len(pages) - 1):
                p_curr = pages[i]
                p_next = pages[i + 1]
                if (
                    p_curr.ends_near_bottom_table
                    and p_next.starts_near_top_table
                    and p_curr.last_table_cols > 0
                    and p_curr.last_table_cols == p_next.first_table_cols
                ):
                    p_curr.table_continues_to_next = True

            return pages

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """Extracts and formats all document pages into a continuous string with [Page N] tags."""
        pages = self.extract_pages(file_path)
        return "\n\n".join(p.text for p in pages)

    def _split_oversized_page(
        self, page: PageData, max_tokens: int
    ) -> List[ChunkData]:
        """Splits an oversized single page along paragraph boundaries into sub-chunks."""
        paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", page.text) if p.strip()
        ]
        sub_chunks: List[ChunkData] = []
        current_paras: List[str] = []
        current_tokens = 0
        part_num = 1

        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            if current_paras and (current_tokens + para_tokens > max_tokens):
                chunk_text = "\n\n".join(current_paras)
                headings = detect_chapter_headings(chunk_text)
                header_line = (
                    "SECTIONS: " + "; ".join(headings)
                    if headings
                    else f"SECTIONS: Page {page.page_number} (Part {part_num})"
                )
                sub_chunks.append(
                    ChunkData(
                        chunk_index=len(sub_chunks),
                        text=chunk_text,
                        token_count=current_tokens,
                        page_numbers=[page.page_number],
                        headings=headings,
                        section_header_line=header_line,
                    )
                )
                part_num += 1
                current_paras = [f"[Page {page.page_number} (Part {part_num})]\n{para}"]
                current_tokens = self._count_tokens(current_paras[0])
            else:
                current_paras.append(para)
                current_tokens += para_tokens

        if current_paras:
            chunk_text = "\n\n".join(current_paras)
            headings = detect_chapter_headings(chunk_text)
            header_line = (
                "SECTIONS: " + "; ".join(headings)
                if headings
                else f"SECTIONS: Page {page.page_number} (Part {part_num})"
            )
            sub_chunks.append(
                ChunkData(
                    chunk_index=len(sub_chunks),
                    text=chunk_text,
                    token_count=current_tokens,
                    page_numbers=[page.page_number],
                    headings=headings,
                    section_header_line=header_line,
                )
            )

        return sub_chunks

    def _make_chunks(self, text: str, max_tokens: int) -> List[str]:
        """
        Legacy text-based chunking interface maintained for backwards compatibility.
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        current: List[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            if current and (current_tokens + para_tokens > max_tokens):
                chunks.append("\n\n".join(current))
                current = [para]
                current_tokens = para_tokens
            else:
                current.append(para)
                current_tokens += para_tokens

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def chunk_pages(self, pages: List[PageData]) -> List[ChunkData]:
        """
        Groups pages into cohesive chunks of ~2,200 tokens (hard max 5 pages),
        splitting at chapter headings (when chunk has >= 2 pages),
        preserving cross-page tables, and repeating the previous chunk's heading.
        """
        if not pages:
            return []

        chunks: List[ChunkData] = []
        current_pages: List[PageData] = []
        current_tokens = 0
        last_heading_of_previous_chunk: Optional[str] = None

        def finalize_chunk(
            chunk_pages: List[PageData],
            context_heading: Optional[str],
        ) -> ChunkData:
            page_texts: List[str] = []
            if context_heading:
                page_texts.append(f"[Previous section context: {context_heading}]")

            for i, p in enumerate(chunk_pages):
                # If page table continues from previous page within this chunk,
                # drop duplicate header row if present
                if i > 0 and chunk_pages[i - 1].table_continues_to_next:
                    page_texts.append(p.text)
                else:
                    page_texts.append(p.text)

            chunk_text = "\n\n".join(page_texts)
            chunk_headings: List[str] = []
            for p in chunk_pages:
                for h in p.headings:
                    if h not in chunk_headings:
                        chunk_headings.append(h)

            start_p = chunk_pages[0].page_number
            end_p = chunk_pages[-1].page_number

            if chunk_headings:
                section_line = "SECTIONS: " + "; ".join(chunk_headings)
            else:
                if start_p == end_p:
                    section_line = f"SECTIONS: Page {start_p}"
                else:
                    section_line = f"SECTIONS: Pages {start_p}-{end_p}"

            return ChunkData(
                chunk_index=len(chunks),
                text=chunk_text,
                token_count=self._count_tokens(chunk_text),
                page_numbers=[p.page_number for p in chunk_pages],
                headings=chunk_headings,
                section_header_line=section_line,
            )

        for page in pages:
            # Check for exceptionally large single page
            if page.token_count > int(self.max_tokens_per_chunk * 1.35) and not current_pages:
                sub_chunks = self._split_oversized_page(page, self.max_tokens_per_chunk)
                chunks.extend(sub_chunks)
                if sub_chunks and sub_chunks[-1].headings:
                    last_heading_of_previous_chunk = sub_chunks[-1].headings[-1]
                continue

            # Determine whether current chunk must split before adding this page
            should_split = False

            if current_pages:
                prev_page = current_pages[-1]
                is_table_continuing = prev_page.table_continues_to_next

                # Condition 1: Structure - starts with chapter heading once chunk >= 2 pages
                if page.first_heading_at_start and len(current_pages) >= 2:
                    should_split = True

                # Condition 2: Token limit exceeded
                elif (current_tokens + page.token_count) > self.max_tokens_per_chunk:
                    # Do not split if table continues, unless overrun cap reached
                    if is_table_continuing:
                        if (
                            len(current_pages) >= self.max_table_overrun_pages
                            or (current_tokens + page.token_count) >= self.max_table_overrun_tokens
                        ):
                            should_split = True
                    else:
                        should_split = True

                # Condition 3: Hard page ceiling reached
                elif len(current_pages) >= self.max_pages_per_chunk:
                    if is_table_continuing:
                        if (
                            len(current_pages) >= self.max_table_overrun_pages
                            or (current_tokens + page.token_count) >= self.max_table_overrun_tokens
                        ):
                            should_split = True
                    else:
                        should_split = True

            if should_split and current_pages:
                new_chunk = finalize_chunk(current_pages, last_heading_of_previous_chunk)
                chunks.append(new_chunk)
                if new_chunk.headings:
                    last_heading_of_previous_chunk = new_chunk.headings[-1]
                current_pages = []
                current_tokens = 0

            current_pages.append(page)
            current_tokens += page.token_count

        if current_pages:
            new_chunk = finalize_chunk(current_pages, last_heading_of_previous_chunk)
            chunks.append(new_chunk)

        # Update chunk indices
        for i, c in enumerate(chunks):
            c.chunk_index = i

        return chunks

    async def _generate(
        self,
        system_prompt: str,
        content: str,
        max_tokens: int,
        stage_name: str = "Generation",
        **kwargs: Any,
    ) -> str:
        """Invokes the configured generation LLM with prompt and content after guard check."""
        prompt_tokens = self._estimate_prompt_tokens(system_prompt, content)

        # Pre-request safety guard: prompt tokens alone cannot exceed the server's context window.
        safety_margin = 150
        max_prompt_capacity = self.server_context_limit - 50

        if prompt_tokens > max_prompt_capacity:
            logger.error(
                "[%s] Prompt tokens (%d) exceed server context window (%d)! Request blocked by pre-request guard.",
                stage_name,
                prompt_tokens,
                self.server_context_limit,
            )
            raise ValueError(
                f"[{stage_name}] Prompt contains {prompt_tokens} tokens, which exceeds the server's context limit "
                f"({self.server_context_limit} tokens). Guard triggered before sending request."
            )

        effective_max_tokens = min(
            max_tokens, max(128, self.server_context_limit - prompt_tokens - safety_margin)
        )
        if effective_max_tokens < max_tokens:
            logger.warning(
                "[%s] Output budget clamped from %d to %d to stay within context limit (%d prompt + %d out <= %d).",
                stage_name,
                max_tokens,
                effective_max_tokens,
                prompt_tokens,
                effective_max_tokens,
                self.server_context_limit,
            )

        llm = get_llm(self.provider_name)
        result = await llm.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            max_tokens=effective_max_tokens,
            **kwargs,
        )
        cleaned = result.strip()
        if not cleaned:
            raise ValueError(f"[{stage_name}] The LLM returned an empty summary.")
        return cleaned

    async def _summarize_chunks(
        self,
        chunks: List[ChunkData],
        semaphore: asyncio.Semaphore,
        **generation_kwargs: Any,
    ) -> List[str]:
        """
        Summarizes chunks concurrently using asyncio.gather and a Semaphore,
        returning results strictly in the original chunk order with stage metrics.
        """
        total = len(chunks)
        logger.info(
            "Starting Map stage: %d chunks to summarize (concurrency=%d, output_budget=%d tokens)",
            total,
            self.max_concurrency,
            self.chunk_output_tokens,
        )
        map_start = time.perf_counter()

        async def process_one(idx: int, chunk: ChunkData) -> Tuple[int, str]:
            async with semaphore:
                chunk_start = time.perf_counter()
                prompt_tokens = self._estimate_prompt_tokens(
                    LONG_CHUNK_SUMMARY_PROMPT, chunk.text
                )
                logger.info(
                    "Map chunk %d/%d starting (%d input tokens, pages %s)",
                    idx + 1,
                    total,
                    prompt_tokens,
                    chunk.page_numbers,
                )
                raw_summary = await self._generate(
                    LONG_CHUNK_SUMMARY_PROMPT,
                    chunk.text,
                    max_tokens=self.chunk_output_tokens,
                    stage_name=f"Map Chunk {idx + 1}/{total}",
                    **generation_kwargs,
                )
                chunk_duration = time.perf_counter() - chunk_start
                out_tokens = self._count_tokens(raw_summary)
                words = len(raw_summary.split())
                is_truncated = "[Warning: summary was cut off]" in raw_summary
                logger.info(
                    "Map chunk %d/%d completed: %d words, %d tokens in %.2fs (prompt: %d tokens%s)",
                    idx + 1,
                    total,
                    words,
                    out_tokens,
                    chunk_duration,
                    prompt_tokens,
                    ", TRUNCATED" if is_truncated else "",
                )
                full_summary = f"{chunk.section_header_line}\n\n{raw_summary}"
                return idx, full_summary

        tasks = [process_one(i, chunk) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)

        # Ensure original order
        results.sort(key=lambda x: x[0])
        map_duration = time.perf_counter() - map_start
        total_out_tokens = sum(self._count_tokens(r[1]) for r in results)
        logger.info(
            "Map stage completed in %.2fs: %d chunks summarized -> %d total tokens",
            map_duration,
            total,
            total_out_tokens,
        )
        return [r[1] for r in results]

    def _split_oversized_summary(self, summary: str, max_tokens: int) -> List[str]:
        """Safely splits a single oversized summary along paragraph boundaries into sub-summaries."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", summary) if p.strip()]
        if not paragraphs:
            return [summary]

        sub_summaries: List[str] = []
        current_paras: List[str] = []
        current_tokens = 0
        part = 1

        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            if current_paras and (current_tokens + para_tokens > max_tokens):
                sub_summaries.append("\n\n".join(current_paras))
                part += 1
                current_paras = [f"[Part {part}]\n{para}"]
                current_tokens = self._count_tokens(current_paras[0])
            else:
                current_paras.append(para)
                current_tokens += para_tokens

        if current_paras:
            sub_summaries.append("\n\n".join(current_paras))

        return sub_summaries

    def _build_reduce_groups(
        self,
        summaries: List[str],
        budget_tokens: int,
        prompt_overhead: int = 300,
    ) -> List[List[str]]:
        """
        Packs summaries into groups preserving their original order such that
        each group's total input tokens fits comfortably within budget_tokens.
        """
        effective_budget = max(500, budget_tokens - prompt_overhead)

        # Normalize any individual oversized summaries
        normalized_summaries: List[str] = []
        for s in summaries:
            s_tokens = self._count_tokens(s)
            if s_tokens > effective_budget:
                logger.warning(
                    "Single summary has %d tokens exceeding group budget %d; splitting safely.",
                    s_tokens,
                    effective_budget,
                )
                normalized_summaries.extend(
                    self._split_oversized_summary(s, effective_budget)
                )
            else:
                normalized_summaries.append(s)

        groups: List[List[str]] = []
        current_group: List[str] = []
        current_tokens = 0

        for summary in normalized_summaries:
            summary_tokens = self._count_tokens(summary) + 15  # per-summary header overhead

            if current_group and (current_tokens + summary_tokens > effective_budget):
                groups.append(current_group)
                current_group = []
                current_tokens = 0

            current_group.append(summary)
            current_tokens += summary_tokens

        if current_group:
            groups.append(current_group)

        return groups

    async def _reduce_summaries(
        self,
        summaries: List[str],
        semaphore: asyncio.Semaphore,
        **generation_kwargs: Any,
    ) -> List[str]:
        """Hierarchically reduces intermediate summaries in groups until combined result fits synthesis threshold."""
        current = summaries
        level = 1
        max_levels = 10
        reduce_start = time.perf_counter()

        while level <= max_levels:
            combined_text = "\n\n".join(current)
            combined_tokens = self._count_tokens(combined_text)

            # Check if reduction is complete
            if len(current) <= 1 or combined_tokens <= self.skip_reduction_threshold:
                logger.info(
                    "Reduction stage complete at level %d: %d summaries (%d tokens) <= synthesis budget (%d tokens)",
                    level - 1,
                    len(current),
                    combined_tokens,
                    self.skip_reduction_threshold,
                )
                return current

            prompt_overhead = self._count_tokens(LONG_REDUCTION_PROMPT) + 100
            groups = self._build_reduce_groups(
                current,
                budget_tokens=self.reduce_input_tokens,
                prompt_overhead=prompt_overhead,
            )

            # Safety check: if grouping made no progress
            if len(groups) >= len(current) and combined_tokens > self.skip_reduction_threshold:
                logger.warning(
                    "Reduction level %d made insufficient grouping progress (%d groups from %d summaries). Forcing tighter group budget.",
                    level,
                    len(groups),
                    len(current),
                )
                groups = self._build_reduce_groups(
                    current,
                    budget_tokens=max(1000, self.reduce_input_tokens // 2),
                    prompt_overhead=prompt_overhead,
                )

            logger.info(
                "Reduction level %d: %d summaries (%d tokens) -> %d groups (target input budget: %d tokens, output budget: %d tokens)",
                level,
                len(current),
                combined_tokens,
                len(groups),
                self.reduce_input_tokens,
                self.reduce_output_tokens,
            )
            level_start = time.perf_counter()

            async def reduce_one(group_idx: int, group_items: List[str]) -> Tuple[int, str]:
                async with semaphore:
                    group_text = "\n\n".join(
                        f"[Section summary {i}]\n{s}"
                        for i, s in enumerate(group_items, start=1)
                    )
                    t_in = self._count_tokens(group_text)
                    t_start = time.perf_counter()
                    res = await self._generate(
                        LONG_REDUCTION_PROMPT,
                        group_text,
                        max_tokens=self.reduce_output_tokens,
                        stage_name=f"Reduce Level {level} Group {group_idx + 1}/{len(groups)}",
                        **generation_kwargs,
                    )
                    dur = time.perf_counter() - t_start
                    t_out = self._count_tokens(res)
                    logger.info(
                        "Reduce group %d/%d (level %d): %d in -> %d out tokens in %.2fs",
                        group_idx + 1,
                        len(groups),
                        level,
                        t_in,
                        t_out,
                        dur,
                    )
                    return group_idx, res

            group_tasks = [reduce_one(i, g) for i, g in enumerate(groups)]
            results = await asyncio.gather(*group_tasks)
            results.sort(key=lambda x: x[0])
            reduced_summaries = [r[1] for r in results]

            level_dur = time.perf_counter() - level_start
            new_combined = "\n\n".join(reduced_summaries)
            new_tokens = self._count_tokens(new_combined)
            logger.info(
                "Reduction level %d finished in %.2fs: %d summaries (%d tokens) -> %d summaries (%d tokens)",
                level,
                level_dur,
                len(current),
                combined_tokens,
                len(reduced_summaries),
                new_tokens,
            )

            current = reduced_summaries
            level += 1

        total_reduce_dur = time.perf_counter() - reduce_start
        logger.info("Total reduction duration: %.2fs", total_reduce_dur)
        return current

    def _perform_coverage_check(
        self,
        final_summary: str,
        chapter_headings: List[str],
    ) -> List[str]:
        """
        Fuzzy matches chapter headings against the final summary.
        Strips leading chapter numbers and matches the first 25 characters case-insensitively.
        """
        missing: List[str] = []
        summary_lower = final_summary.lower()

        for heading in chapter_headings:
            # Exclude fallback page-range headings
            if re.match(r"^Pages?\s+\d+", heading, re.IGNORECASE):
                continue

            cleaned_title = re.sub(r"^\d+\.\s*", "", heading).strip().lower()
            needle = cleaned_title[:25].strip()
            if needle and needle not in summary_lower:
                missing.append(heading)

        return missing

    async def summarize(
        self, file_path: Union[str, Path], **kwargs: Any
    ) -> str:
        """
        Extracts, chunks, summarizes in parallel, optionally reduces,
        and generates the final cohesive summary with coverage verification and full instrumentation.
        """
        pipeline_start = time.perf_counter()

        # Stage 1: PDF Extraction
        extract_start = time.perf_counter()
        pages = self.extract_pages(file_path)
        extract_duration = time.perf_counter() - extract_start

        if not pages:
            raise ValueError("The PDF document contains 0 pages.")

        total_extracted_chars = sum(len(p.text) for p in pages)
        total_extracted_tokens = sum(p.token_count for p in pages)
        logger.info(
            "PDF Extraction completed in %.2fs: %d pages, %d chars, %d tokens",
            extract_duration,
            len(pages),
            total_extracted_chars,
            total_extracted_tokens,
        )

        # Stage 2: Chunking
        chunk_start = time.perf_counter()
        chunks = self.chunk_pages(pages)
        chunk_duration = time.perf_counter() - chunk_start

        if not chunks:
            raise ValueError("The PDF document contains no usable text.")

        total_tokens = sum(c.token_count for c in chunks)
        logger.info(
            "Chunking completed in %.2fs: %d chunks, %d estimated tokens across %d pages",
            chunk_duration,
            len(chunks),
            total_tokens,
            len(pages),
        )

        for c in chunks:
            logger.info(
                "Chunk %d: %d tokens, pages %s, %s",
                c.chunk_index + 1,
                c.token_count,
                c.page_numbers,
                c.section_header_line,
            )

        generation_kwargs = dict(kwargs)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # Stage 3: Parallel Chunk Summarization (Map)
        chunk_summaries = await self._summarize_chunks(
            chunks, semaphore, **generation_kwargs
        )

        # Stage 4: Hierarchical Reduction (Reduce)
        combined_summaries_text = "\n\n".join(chunk_summaries)
        combined_tokens = self._count_tokens(combined_summaries_text)

        if combined_tokens <= self.skip_reduction_threshold or len(chunk_summaries) <= 1:
            logger.info(
                "Skipping reduction stage: combined chunk summaries (%d tokens) <= threshold (%d tokens)",
                combined_tokens,
                self.skip_reduction_threshold,
            )
            synthesis_input = combined_summaries_text
        else:
            logger.info(
                "Executing reduction stage: combined chunk summaries (%d tokens) > threshold (%d tokens)",
                combined_tokens,
                self.skip_reduction_threshold,
            )
            reduced = await self._reduce_summaries(
                chunk_summaries, semaphore, **generation_kwargs
            )
            synthesis_input = "\n\n".join(reduced)

        # Stage 5: Prepare Final Synthesis Input
        cleaned_synthesis_input = re.sub(
            r"(?m)^SECTIONS:.*$\n?", "", synthesis_input
        ).strip()

        all_chapter_headings: List[str] = []
        for c in chunks:
            for h in c.headings:
                if h not in all_chapter_headings:
                    all_chapter_headings.append(h)

        if all_chapter_headings:
            chapters_context = (
                "The document has these chapters:\n"
                + "\n".join(f"- {h}" for h in all_chapter_headings)
                + "\n\nEvery one must appear in the final summary.\n\n"
            )
            final_input = f"{chapters_context}{cleaned_synthesis_input}"
        else:
            final_input = cleaned_synthesis_input

        # Stage 6: Final Summary Generation
        final_prompt_tokens = self._estimate_prompt_tokens(
            LONG_FINAL_SUMMARY_PROMPT, final_input
        )
        logger.info(
            "Starting Final Synthesis: %d prompt tokens, %d output budget",
            final_prompt_tokens,
            self.final_output_tokens,
        )
        final_start = time.perf_counter()
        final_summary = await self._generate(
            LONG_FINAL_SUMMARY_PROMPT,
            final_input,
            max_tokens=self.final_output_tokens,
            stage_name="Final Synthesis",
            **generation_kwargs,
        )
        final_duration = time.perf_counter() - final_start
        final_tokens = self._count_tokens(final_summary)
        logger.info(
            "Final Synthesis completed in %.2fs: %d tokens generated",
            final_duration,
            final_tokens,
        )

        # Stage 7: Coverage Check with Fuzzy Matching
        if all_chapter_headings:
            missing_sections = self._perform_coverage_check(
                final_summary, all_chapter_headings
            )
            if missing_sections:
                logger.warning(
                    "Coverage check identified %d missing chapters: %s. Re-running final synthesis.",
                    len(missing_sections),
                    missing_sections,
                )
                coverage_note = (
                    "Note: The following chapters were missing or not adequately covered in the summary:\n"
                    + "\n".join(f"- {s}" for s in missing_sections)
                    + "\nPlease revise the summary to ensure every one of these chapters is thoroughly covered.\n\n"
                )
                retry_input = f"{coverage_note}{final_input}"
                retry_prompt_tokens = self._estimate_prompt_tokens(
                    LONG_FINAL_SUMMARY_PROMPT, retry_input
                )
                logger.info(
                    "Re-running Final Synthesis for coverage revision: %d prompt tokens",
                    retry_prompt_tokens,
                )
                final_summary = await self._generate(
                    LONG_FINAL_SUMMARY_PROMPT,
                    retry_input,
                    max_tokens=self.final_output_tokens,
                    stage_name="Final Synthesis Coverage Revision",
                    **generation_kwargs,
                )
                missing_after = self._perform_coverage_check(
                    final_summary, all_chapter_headings
                )
                if missing_after:
                    logger.warning(
                        "After coverage revision, %d chapters remain unconfirmed: %s",
                        len(missing_after),
                        missing_after,
                    )
                else:
                    logger.info("Coverage revision succeeded: all chapters now verified.")
            else:
                logger.info(
                    "Coverage check passed: all %d chapter headings covered!",
                    len(all_chapter_headings),
                )

        pipeline_duration = time.perf_counter() - pipeline_start
        logger.info(
            "Long-document summarization finished in %.2fs: %d pages -> %d chunks -> %d final tokens",
            pipeline_duration,
            len(pages),
            len(chunks),
            self._count_tokens(final_summary),
        )

        return final_summary
