"""Unit tests for pure ChatService methods (no DB, no network)."""

import uuid

from src.models.user import User
from src.schemas.rag import RetrievedChunk
from src.services.chat_service import ChatService

_HAIKU = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-6"


def _make_user(tier: str = "free", preferred_model: str = _HAIKU) -> User:
    return User(
        id="user_test_abc123",
        email="test@example.com",
        credits_balance=50,
        tier=tier,
        preferred_model=preferred_model,
    )


def _make_chunk(content: str = "test content") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        content=content,
        source_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        memory_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        final_score=0.9,
        semantic_score=0.85,
        recency_weight=0.7,
    )


class TestResolveModel:
    def test_no_alias_uses_user_preferred_model(self):
        user = _make_user(preferred_model=_HAIKU)
        model, cost = ChatService.resolve_model(None, user)
        assert model == _HAIKU
        assert cost == 3

    def test_haiku_alias_resolves_to_full_id(self):
        user = _make_user()
        model, cost = ChatService.resolve_model("haiku", user)
        assert model == _HAIKU
        assert cost == 3

    def test_sonnet_alias_resolves_for_pro_user(self):
        user = _make_user(tier="pro")
        model, cost = ChatService.resolve_model("sonnet", user)
        assert model == _SONNET
        assert cost == 8

    def test_free_tier_cannot_use_sonnet(self):
        """Free tier request for sonnet is silently downgraded to haiku."""
        user = _make_user(tier="free")
        model, cost = ChatService.resolve_model("sonnet", user)
        assert model == _HAIKU
        assert cost == 3

    def test_unknown_alias_falls_back_to_haiku_cost(self):
        user = _make_user()
        model, cost = ChatService.resolve_model("gpt-4", user)
        assert cost == 3  # unknown model gets haiku cost


class TestBuildHistory:
    def test_returns_role_and_content_only(self):
        svc = ChatService()
        messages = [
            {"role": "user", "content": "Hello", "created_at": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "Hi!", "created_at": "2026-01-01T00:00:01"},
        ]
        history = svc.build_history(messages)
        assert history == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

    def test_empty_messages_returns_empty_list(self):
        svc = ChatService()
        assert svc.build_history([]) == []


class TestBuildSystemPrompt:
    def test_includes_source_id_not_filename(self):
        """source_filename does not exist on RetrievedChunk — must use str(source_id)."""
        svc = ChatService()
        chunk = _make_chunk("My CV content")
        prompt = svc.build_system_prompt([chunk])
        assert "11111111-1111-1111-1111-111111111111" in prompt
        assert "My CV content" in prompt

    def test_empty_chunks_still_returns_valid_prompt(self):
        svc = ChatService()
        prompt = svc.build_system_prompt([])
        assert "Ravenbase" in prompt

    def test_memory_context_wrapped_in_xml(self):
        """RULE 10: user-controlled content must be in XML boundary tags."""
        svc = ChatService()
        chunk = _make_chunk("sensitive content")
        prompt = svc.build_system_prompt([chunk])
        assert "<memory_context>" in prompt
        assert "</memory_context>" in prompt


class TestExtractCitations:
    def test_uses_source_id_not_filename(self):
        svc = ChatService()
        chunk = _make_chunk("hello world " * 20)  # 240 chars
        citations = svc.extract_citations([chunk])
        assert len(citations) == 1
        assert citations[0].source_id == "11111111-1111-1111-1111-111111111111"
        assert citations[0].memory_id == "22222222-2222-2222-2222-222222222222"

    def test_content_preview_capped_at_200_chars(self):
        svc = ChatService()
        chunk = _make_chunk("x" * 300)
        citations = svc.extract_citations([chunk])
        assert len(citations[0].content_preview) == 200

    def test_null_memory_id_handled(self):
        svc = ChatService()
        chunk = RetrievedChunk(
            chunk_id="c1",
            content="text",
            source_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            memory_id=None,
            final_score=0.5,
            semantic_score=0.5,
            recency_weight=0.5,
        )
        citations = svc.extract_citations([chunk])
        assert citations[0].memory_id is None
