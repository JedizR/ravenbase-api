"""Unit tests for DoclingAdapter.

Docling is imported lazily inside _sync_parse_and_chunk. We inject mocks via
sys.modules so no real Docling installation is needed during unit tests.
"""

from unittest.mock import MagicMock, patch


def _make_docling_sys_modules(markdown: str) -> dict:
    """Return a sys.modules patch dict that stubs out all docling sub-modules."""
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = markdown

    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_conv_instance = MagicMock()
    mock_conv_instance.convert.return_value = mock_result

    mock_docling_dc = MagicMock()
    mock_docling_dc.DocumentConverter = MagicMock(return_value=mock_conv_instance)

    mock_docling_core_io = MagicMock()
    mock_docling_core_io.DocumentStream = MagicMock(return_value=MagicMock())

    return {
        "docling": MagicMock(),
        "docling.document_converter": mock_docling_dc,
        "docling.datamodel": MagicMock(),
        "docling.datamodel.pipeline_options": MagicMock(),
        "docling.datamodel.base_models": MagicMock(),
        "docling_core": MagicMock(),
        "docling_core.types": MagicMock(),
        "docling_core.types.io": mock_docling_core_io,
    }


def test_parse_and_chunk_returns_list_of_dicts() -> None:
    """_sync_parse_and_chunk returns list of dicts with required keys."""
    md = "Hello world.\n\nThis is paragraph two.\n\nAnd paragraph three."

    with patch.dict("sys.modules", _make_docling_sys_modules(md)):
        from src.adapters.docling_adapter import DoclingAdapter  # noqa: PLC0415

        adapter = DoclingAdapter()
        chunks = adapter._sync_parse_and_chunk(b"%PDF fake", "test.pdf")

    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "text" in chunk
        assert "page_number" in chunk
        assert "chunk_index" in chunk
        assert isinstance(chunk["text"], str)
        assert len(chunk["text"]) > 0


def test_parse_and_chunk_respects_size_limit() -> None:
    """Chunks stay within ~3000 chars (2048 limit + overlap)."""
    long_para = "A" * 300
    md = "\n\n".join([long_para] * 20)  # 20 × 300 = 6000 chars total

    with patch.dict("sys.modules", _make_docling_sys_modules(md)):
        from src.adapters.docling_adapter import DoclingAdapter  # noqa: PLC0415

        adapter = DoclingAdapter()
        chunks = adapter._sync_parse_and_chunk(b"%PDF fake", "test.pdf")

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 3000  # generous bound; real limit 2048 + overlap


def test_parse_and_chunk_chunk_index_is_sequential() -> None:
    """chunk_index values are 0, 1, 2, … in order."""
    long_para = "Word " * 100
    md = "\n\n".join([long_para] * 30)

    with patch.dict("sys.modules", _make_docling_sys_modules(md)):
        from src.adapters.docling_adapter import DoclingAdapter  # noqa: PLC0415

        adapter = DoclingAdapter()
        chunks = adapter._sync_parse_and_chunk(b"%PDF fake", "test.pdf")

    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i
