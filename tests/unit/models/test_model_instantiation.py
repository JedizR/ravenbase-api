# tests/unit/models/test_model_instantiation.py
import uuid

from src.models.conflict import Conflict, ConflictStatus
from src.models.credit import CreditTransaction
from src.models.job_status import JobStatus
from src.models.meta_document import MetaDocument
from src.models.profile import SystemProfile
from src.models.source import Source, SourceAuthorityWeight, SourceStatus
from src.models.user import User


def test_user_default_fields() -> None:
    user = User(email="test@example.com")
    assert user.tier == "free"
    assert user.credits_balance == 0
    assert user.is_active is True
    assert user.preferred_model == "claude-haiku-4-5-20251001"
    assert user.referral_code == ""
    assert user.referral_reward_claimed is False
    assert user.is_archived is False
    assert user.notify_welcome is True
    assert user.notify_low_credits is True
    assert user.notify_ingestion_complete is True
    assert user.notify_account_deletion is True
    assert user.referred_by_user_id is None


def test_system_profile_default_fields() -> None:
    uid = "user_test_abc123"
    profile = SystemProfile(user_id=uid, name="Work")
    assert profile.is_default is False
    assert profile.description is None
    assert profile.icon is None
    assert profile.color is None
    assert isinstance(profile.id, uuid.UUID)


def test_source_default_fields() -> None:
    uid = "user_test_abc123"
    source = Source(
        user_id=uid,
        original_filename="notes.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        storage_path="uploads/notes.pdf",
        sha256_hash="abc123",
        file_size_bytes=1024,
    )
    assert source.status == SourceStatus.PENDING
    assert source.chunk_count is None
    assert source.node_count is None
    assert source.profile_id is None
    assert isinstance(source.id, uuid.UUID)


def test_source_authority_weight_defaults() -> None:
    uid = "user_test_abc123"
    saw = SourceAuthorityWeight(user_id=uid, source_type="pdf")
    assert saw.weight == 5


def test_conflict_default_fields() -> None:
    uid = "user_test_abc123"
    conflict = Conflict(
        user_id=uid,
        incumbent_memory_id="mem-001",
        challenger_memory_id="mem-002",
        incumbent_content="I use Python.",
        challenger_content="I use Go.",
        ai_classification="CONTRADICTION",
        confidence_score=0.92,
    )
    assert conflict.status == ConflictStatus.PENDING
    assert conflict.resolution_note is None
    assert conflict.resolved_at is None
    assert conflict.profile_id is None
    assert isinstance(conflict.id, uuid.UUID)


def test_meta_document_default_fields() -> None:
    uid = "user_test_abc123"
    doc = MetaDocument(
        user_id=uid,
        title="My Knowledge Summary",
        original_prompt="Summarize my Python knowledge",
    )
    assert doc.contributing_memory_ids == []
    assert doc.credits_consumed == 0
    assert doc.model_used == "claude-sonnet"
    assert doc.parsed_intent is None
    assert doc.profile_id is None
    assert isinstance(doc.id, uuid.UUID)


def test_credit_transaction_fields() -> None:
    uid = "user_test_abc123"
    tx = CreditTransaction(user_id=uid, amount=-5, balance_after=195, operation="ingest_page")
    assert tx.reference_id is None


def test_job_status_default_fields() -> None:
    uid = "user_test_abc123"
    job = JobStatus(id="arq:job:abc123", user_id=uid, job_type="ingestion")
    assert job.status == "queued"
    assert job.progress_pct == 0
    assert job.message is None
    assert job.source_id is None


def test_graph_query_request_schema_exists() -> None:
    from src.schemas.graph import GraphQueryRequest  # noqa: PLC0415

    req = GraphQueryRequest(query="test")
    assert req.query == "test"
    assert req.limit == 20
    assert req.profile_id is None


def test_graph_query_response_schema_exists() -> None:
    from src.schemas.graph import GraphQueryResponse, GraphResponse  # noqa: PLC0415

    resp = GraphQueryResponse(
        cypher="MATCH (n) RETURN n",
        results=GraphResponse(nodes=[], edges=[]),
        explanation="Found 0 nodes.",
        query_time_ms=5,
    )
    assert resp.query_time_ms == 5
