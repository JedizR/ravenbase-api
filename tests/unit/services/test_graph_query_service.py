# tests/unit/services/test_graph_query_service.py
"""Unit tests for GraphQueryService (STORY-029).

All external adapters mocked. No live Neo4j, LLM, or DB required.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

TEST_TENANT_ID = "tenant-unit-029"

# ---------------------------------------------------------------------------
# inject_tenant_filter tests
# ---------------------------------------------------------------------------


def test_inject_tenant_filter_no_existing_where() -> None:
    from src.services.graph_query_service import inject_tenant_filter  # noqa: PLC0415

    cypher = "MATCH (n:Memory) RETURN n LIMIT 20"
    result = inject_tenant_filter(cypher)
    assert "n.tenant_id = $tenant_id" in result
    # Must use Cypher $param syntax, NOT a string literal
    assert "$tenant_id" in result
    assert TEST_TENANT_ID not in result


def test_inject_tenant_filter_preserves_existing_where() -> None:
    from src.services.graph_query_service import inject_tenant_filter  # noqa: PLC0415

    cypher = "MATCH (n:Memory) WHERE n.is_valid = true RETURN n LIMIT 20"
    result = inject_tenant_filter(cypher)
    assert "n.tenant_id = $tenant_id" in result
    assert "n.is_valid = true" in result


def test_inject_tenant_filter_multi_match() -> None:
    from src.services.graph_query_service import inject_tenant_filter  # noqa: PLC0415

    cypher = "MATCH (m:Memory)-[:EXTRACTED_FROM]->(c:Concept) RETURN m, c LIMIT 10"
    result = inject_tenant_filter(cypher)
    assert "$tenant_id" in result
    # Relationship pattern must remain intact (not split by WHERE insertion)
    assert "-[:EXTRACTED_FROM]->(c:Concept)" in result


def test_inject_tenant_filter_no_string_literal_interpolation() -> None:
    from src.services.graph_query_service import inject_tenant_filter  # noqa: PLC0415

    cypher = "MATCH (n) RETURN n LIMIT 5"
    result = inject_tenant_filter(cypher)
    assert "$tenant_id" in result
    assert "= '" not in result  # No string-literal injection


# ---------------------------------------------------------------------------
# CYPHER_WRITE_KEYWORDS regex tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_cypher",
    [
        "CREATE (n:Memory {content: 'x'})",
        "MERGE (n:Node {id: 1})",
        "MATCH (n) SET n.name = 'x'",
        "MATCH (n) DELETE n",
        "MATCH (n) REMOVE n.prop",
        "DROP INDEX my_index",
        "merge (n:Node)",
        "Delete n",
    ],
)
def test_write_keywords_detects_unsafe(bad_cypher: str) -> None:
    from src.services.graph_query_service import CYPHER_WRITE_KEYWORDS  # noqa: PLC0415

    assert CYPHER_WRITE_KEYWORDS.search(bad_cypher)


def test_write_keywords_safe_match_is_clean() -> None:
    from src.services.graph_query_service import CYPHER_WRITE_KEYWORDS  # noqa: PLC0415

    safe = (
        "MATCH (m:Memory)-[:EXTRACTED_FROM]->(c:Concept) "
        "WHERE m.tenant_id = $tenant_id "
        "RETURN labels(m)[0] AS n_type, properties(m) AS n_props, "
        "type(r) AS r_type, properties(r) AS r_props, "
        "labels(c)[0] AS m_type, properties(c) AS m_props LIMIT 20"
    )
    assert not CYPHER_WRITE_KEYWORDS.search(safe)


# ---------------------------------------------------------------------------
# GraphQueryService.execute_nl_query unit tests
# ---------------------------------------------------------------------------

_SAFE_CYPHER = (
    "MATCH (m:Memory) WHERE m.tenant_id = $tenant_id "
    "RETURN labels(m)[0] AS n_type, properties(m) AS n_props, "
    "null AS r_type, null AS r_props, null AS m_type, null AS m_props LIMIT 20"
)


def _make_mock_llm(cypher_response: str) -> MagicMock:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    mock = MagicMock(spec=LLMRouter)
    mock.complete = AsyncMock(return_value=cypher_response)
    return mock


def _make_mock_neo4j(rows: list[dict]) -> MagicMock:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    mock = MagicMock(spec=Neo4jAdapter)
    mock.run_query = AsyncMock(return_value=rows)
    return mock


@pytest.mark.asyncio
async def test_execute_nl_query_happy_path_returns_all_fields() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    memory_id = "mem-001"
    rows = [
        {
            "n_type": "Memory",
            "n_props": {"memory_id": memory_id, "content": "test", "tenant_id": TEST_TENANT_ID},
            "r_type": None,
            "r_props": None,
            "m_type": None,
            "m_props": None,
        }
    ]
    svc = GraphQueryService(
        llm_router=_make_mock_llm(_SAFE_CYPHER), neo4j_adapter=_make_mock_neo4j(rows)
    )
    result = await svc.execute_nl_query(
        query="Show my memories", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
    )
    assert result.cypher
    assert len(result.results.nodes) == 1
    assert result.results.nodes[0].id == memory_id
    assert isinstance(result.explanation, str) and len(result.explanation) > 0
    assert isinstance(result.query_time_ms, int) and result.query_time_ms >= 0


@pytest.mark.asyncio
async def test_execute_nl_query_unsafe_cypher_raises_http422() -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415, I001

    mock_neo4j = _make_mock_neo4j([])
    svc = GraphQueryService(
        llm_router=_make_mock_llm("CREATE (n:Memory {content: 'injected'})"),
        neo4j_adapter=mock_neo4j,
    )
    with pytest.raises(HTTPException) as exc_info:
        await svc.execute_nl_query(
            query="Delete all", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "UNSAFE_QUERY"
    mock_neo4j.run_query.assert_not_called()  # never reaches Neo4j


@pytest.mark.asyncio
async def test_execute_nl_query_empty_results_explanation() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    svc = GraphQueryService(
        llm_router=_make_mock_llm(_SAFE_CYPHER), neo4j_adapter=_make_mock_neo4j([])
    )
    result = await svc.execute_nl_query(
        query="Find projects", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
    )
    assert result.results.nodes == []
    assert result.results.edges == []
    assert result.explanation == "No memories found matching your query."


@pytest.mark.asyncio
async def test_execute_nl_query_llm_task_is_cypher_generation() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    mock_llm = _make_mock_llm(_SAFE_CYPHER)
    svc = GraphQueryService(llm_router=mock_llm, neo4j_adapter=_make_mock_neo4j([]))
    await svc.execute_nl_query(
        query="My Python skills", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
    )
    call_kwargs = mock_llm.complete.call_args
    task_arg = call_kwargs.kwargs.get("task") or (call_kwargs.args[0] if call_kwargs.args else None)
    assert task_arg == "cypher_generation"
    assert "response_format" not in (call_kwargs.kwargs or {})


@pytest.mark.asyncio
async def test_execute_nl_query_tenant_id_passed_as_run_query_param() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    llm_cypher = (
        "MATCH (m:Memory) "
        "RETURN labels(m)[0] AS n_type, properties(m) AS n_props, "
        "null AS r_type, null AS r_props, null AS m_type, null AS m_props LIMIT 20"
    )
    mock_neo4j = _make_mock_neo4j([])
    svc = GraphQueryService(llm_router=_make_mock_llm(llm_cypher), neo4j_adapter=mock_neo4j)
    await svc.execute_nl_query(query="test", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20)
    call_kwargs = mock_neo4j.run_query.call_args
    assert call_kwargs.kwargs.get("tenant_id") == TEST_TENANT_ID
    cypher_arg = call_kwargs.args[0]
    assert TEST_TENANT_ID not in cypher_arg


@pytest.mark.asyncio
async def test_execute_nl_query_limit_capped_at_50_in_prompt() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    captured: list[dict] = []

    async def _capture(task, messages, **kwargs):
        captured.extend(messages)
        return _SAFE_CYPHER

    mock_llm = MagicMock()
    mock_llm.complete = _capture
    svc = GraphQueryService(llm_router=mock_llm, neo4j_adapter=_make_mock_neo4j([]))
    await svc.execute_nl_query(query="test", tenant_id=TEST_TENANT_ID, profile_id=None, limit=100)
    prompt_text = captured[0]["content"]
    assert "50" in prompt_text
    assert "100" not in prompt_text


@pytest.mark.asyncio
async def test_execute_nl_query_user_query_in_xml_tags() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    captured: list[dict] = []

    async def _capture(task, messages, **kwargs):
        captured.extend(messages)
        return _SAFE_CYPHER

    mock_llm = MagicMock()
    mock_llm.complete = _capture
    svc = GraphQueryService(llm_router=mock_llm, neo4j_adapter=_make_mock_neo4j([]))
    test_query = "Show me all Python projects from 2023"
    await svc.execute_nl_query(
        query=test_query, tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
    )
    prompt = captured[0]["content"]
    assert "<user_query>" in prompt
    assert test_query in prompt
    assert "</user_query>" in prompt


@pytest.mark.asyncio
async def test_execute_nl_query_query_time_ms_non_negative_int() -> None:
    from src.services.graph_query_service import GraphQueryService  # noqa: PLC0415

    svc = GraphQueryService(
        llm_router=_make_mock_llm(_SAFE_CYPHER), neo4j_adapter=_make_mock_neo4j([])
    )
    result = await svc.execute_nl_query(
        query="test", tenant_id=TEST_TENANT_ID, profile_id=None, limit=20
    )
    assert isinstance(result.query_time_ms, int)
    assert result.query_time_ms >= 0
