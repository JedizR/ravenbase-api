"""DoclingAdapter for document parsing and chunking.

Wraps Docling document parsing and paragraph-aware chunking.
All Docling imports are INSIDE _sync_parse_and_chunk() (RULE 6: lazy heavy imports).
Call parse_and_chunk() — it runs the sync method in a thread executor.
"""

from __future__ import annotations

import asyncio

import structlog

from src.adapters.base import BaseAdapter

logger = structlog.get_logger()

_CHUNK_MAX_CHARS = 2048  # ~512 tokens at 4 chars/token
_CHUNK_OVERLAP_CHARS = 200  # ~50 tokens overlap


class DoclingAdapter(BaseAdapter):
    """Wraps Docling document parsing and paragraph-aware chunking.

    All Docling imports are INSIDE _sync_parse_and_chunk() (RULE 6: lazy heavy imports).
    Call parse_and_chunk() — it runs the sync method in a thread executor.
    """

    async def parse_and_chunk(
        self,
        content: bytes,
        filename: str,
    ) -> list[dict]:
        """Parse document and return chunks. Runs Docling in a thread executor.

        Args:
            content: Raw document bytes (PDF, DOCX, etc.)
            filename: Original filename for logging and format detection

        Returns:
            List of dicts: {text: str, page_number: int, chunk_index: int}
        """
        log = logger.bind(filename=filename, size_bytes=len(content))
        log.info("docling.parse.started")
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(None, self._sync_parse_and_chunk, content, filename)
        log.info("docling.parse.completed", chunk_count=len(chunks))
        return chunks

    def _sync_parse_and_chunk(self, content: bytes, filename: str) -> list[dict]:
        """Synchronous Docling parse + chunking. Called via run_in_executor only.

        Args:
            content: Raw document bytes
            filename: Filename for format detection

        Returns:
            List of chunks with text, page_number, and chunk_index
        """
        import io  # noqa: PLC0415

        from docling.datamodel.base_models import InputFormat  # noqa: PLC0415
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # noqa: PLC0415
        from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: PLC0415
        from docling_core.types.io import DocumentStream  # noqa: PLC0415

        options = PdfPipelineOptions(
            generate_page_images=False,
            generate_picture_images=False,
        )
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        stream = DocumentStream(name=filename, stream=io.BytesIO(content))
        result = converter.convert(stream)
        markdown = result.document.export_to_markdown()
        return _chunk_markdown(markdown)

    def cleanup(self) -> None:
        """No external resources to clean up."""
        pass


def _chunk_markdown(markdown: str) -> list[dict]:
    """Split markdown into overlapping chunks respecting paragraph boundaries.

    Strategy:
    - Split on double-newline (paragraph boundary)
    - Greedily combine paragraphs until _CHUNK_MAX_CHARS is reached
    - On overflow: emit chunk, start next chunk with overlap prefix

    Args:
        markdown: Full document markdown text

    Returns:
        List of dicts: {text: str, page_number: int, chunk_index: int}
    """
    paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[dict] = []
    current_parts: list[str] = []
    current_len = 0
    overlap_text = ""

    for para in paragraphs:
        para_len = len(para)
        # Calculate length including separator between paragraphs
        sep_len = 2 if current_parts else 0  # "\n\n"
        new_len = current_len + sep_len + para_len

        if new_len > _CHUNK_MAX_CHARS and current_parts:
            # Emit current chunk
            text = "\n\n".join(current_parts)
            chunks.append(
                {
                    "text": (overlap_text + " " + text).strip() if overlap_text else text,
                    "page_number": 0,
                    "chunk_index": len(chunks),
                }
            )
            # Build overlap from end of emitted chunk
            overlap_text = (
                text[-_CHUNK_OVERLAP_CHARS:] if len(text) > _CHUNK_OVERLAP_CHARS else text
            )
            current_parts = [para]
            current_len = para_len
        else:
            current_parts.append(para)
            current_len = new_len

    # Emit final chunk
    if current_parts:
        text = "\n\n".join(current_parts)
        chunks.append(
            {
                "text": (overlap_text + " " + text).strip() if overlap_text else text,
                "page_number": 0,
                "chunk_index": len(chunks),
            }
        )

    return chunks
