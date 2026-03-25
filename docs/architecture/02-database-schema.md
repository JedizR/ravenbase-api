# Architecture — 02. Database Schema

> **Cross-references:** `architecture/00-system-overview.md` | `development/02-coding-standards.md`
>
> **AGENT NOTE:** Use this as the source of truth for all data models. Implement Alembic migrations for every schema change. Never use `create_all()` in production.

---

## PostgreSQL Schema (SQLModel + Alembic)

### Naming Conventions (from BMAD blueprint)

```
Tables:       plural snake_case       → users, sources, conflicts
Columns:      singular snake_case     → tenant_id, created_at
Primary keys: always UUID "id"
Foreign keys: {singular_table}_id    → user_id, source_id
Booleans:     is_ or has_ prefix     → is_active, has_paid
Timestamps:   _at suffix             → created_at, resolved_at
Indexes:      idx_{table}_{column}   → idx_sources_user_id
```

---

### Table: `users`

```python
# src/models/user.py
import uuid
from datetime import datetime, UTC
from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        # NOTE: This id MUST match the Clerk user_id (UUID format)
        # Set during onboarding webhook from Clerk
    )
    email: str = Field(unique=True, index=True)
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    tier: str = Field(default="free")          # "free" | "pro" | "team"
    credits_balance: int = Field(default=200)   # Free tier starts with 200
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    preferred_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Model for user-initiated generation tasks (meta-docs, chat). "
                    "Must be one of: claude-haiku-4-5-20251001, claude-sonnet-4-6"
    )
    # Email notification preferences — all default to True (opt-out model)
    notify_welcome: bool = Field(default=True)
    notify_low_credits: bool = Field(default=True)
    notify_ingestion_complete: bool = Field(default=True)
    # ^ notify_ingestion_complete only applies to files > 2MB (see STORY-032)
    # Referral system
    referral_code: str = Field(
        default="",
        unique=True,
        index=True,
        description="First 8 chars of UUID, uppercase. Set on user creation. "
                    "Used as: ravenbase.app/register?ref=CODE"
    )
    referred_by_user_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="UUID of referring user. NULL if organic signup."
    )
    referral_reward_claimed: bool = Field(
        default=False,
        description="True after referrer has been credited for this user's first upload. "
                    "Prevents double-crediting."
    )
    low_credits_email_sent_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last low-credits warning email. "
                    "Prevents sending the same warning multiple times per billing period. "
                    "Reset to None when monthly credits refresh."
    )

    # Cold data lifecycle (STORY-037)
    last_active_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Timestamp of last authenticated API request. Updated at most once "
                    "per day per user (debounced in FastAPI middleware) to minimize DB writes."
    )
    is_archived: bool = Field(
        default=False,
        description="True when a Free-tier user's data has been purged after 180 days "
                    "of inactivity. User record and Clerk identity are KEPT — only storage "
                    "data (files, vectors, graph) is deleted. User can still log in and "
                    "re-upload. Pro/Team users are NEVER archived."
    )
    notify_account_deletion: bool = Field(
        default=True,
        description="Whether to send the 30-day inactivity warning email (day 150 warning). "
                    "Part of the notify_* family — user can disable in Settings → Notifications."
    )
```

> **Model selection policy:**
> `preferred_model` applies ONLY to user-initiated generation tasks:
> Meta-Document synthesis (STORY-016) and Chat (STORY-026).
>
> These tasks always use their own fixed models regardless of `preferred_model`:
> - Entity extraction → `claude-haiku-4-5-20251001` (STORY-009)
> - Conflict classification → `claude-haiku-4-5-20251001` (STORY-012)
> - Cypher generation → `claude-haiku-4-5-20251001` (STORY-029)
>
> Rationale: automated background tasks build the knowledge graph's structural
> integrity. Model variance in those tasks would produce inconsistent graph quality
> across ingestion sessions.

### Table: `data_retention_logs`

```python
class DataRetentionLog(SQLModel, table=True):
    """
    Compliance audit trail for cold-data lifecycle events.
    Records every warning sent and every purge executed.
    Retained indefinitely (never purged — it's an audit log).
    """
    __tablename__ = "data_retention_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        description="The affected user. FK retained even after User.is_archived=True."
    )
    event_type: str = Field(
        description="'warning_sent' | 'data_purged'"
    )
    days_inactive: int = Field(
        description="How many days the user had been inactive at the time of this event."
    )

    # Populated on 'data_purged' events only
    sources_deleted: Optional[int] = Field(default=None)
    qdrant_vectors_deleted: Optional[int] = Field(default=None)
    neo4j_nodes_deleted: Optional[int] = Field(default=None)
    storage_bytes_freed: Optional[int] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

### Table: `referral_transactions`

```python
class ReferralTransaction(SQLModel, table=True):
    """Audit trail for all referral reward events."""
    __tablename__ = "referral_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    referrer_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    referee_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    referrer_credits_awarded: int = Field(default=200)
    referee_credits_awarded: int = Field(default=200)
    trigger_event: str = Field(default="first_upload")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Table: `system_profiles`

```python
# src/models/profile.py
class SystemProfile(SQLModel, table=True):
    __tablename__ = "system_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    name: str                              # "Work — Full Stack", "Academic", "Personal"
    description: Optional[str] = None
    icon: Optional[str] = None             # Emoji or icon name
    is_default: bool = Field(default=False)
    color: Optional[str] = None            # Hex color for UI badge
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        # Constraint: user can only have one default profile
        pass
```

### Table: `sources`

```python
# src/models/source.py
class SourceStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXING = "indexing"       # chunks embedded, graph extraction pending
    COMPLETED = "completed"
    FAILED = "failed"

class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")
    original_filename: str
    file_type: str                         # "pdf" | "txt" | "md" | "json" | "zip"
    mime_type: str
    storage_path: str                      # Supabase Storage path
    sha256_hash: str = Field(index=True)   # For deduplication
    file_size_bytes: int
    status: str = Field(default=SourceStatus.PENDING, index=True)
    chunk_count: Optional[int] = None
    node_count: Optional[int] = None       # Neo4j nodes created
    error_message: Optional[str] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
```

### Table: `source_authority_weights`

```python
# Used by auto-resolution in conflict_worker
class SourceAuthorityWeight(SQLModel, table=True):
    __tablename__ = "source_authority_weights"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    source_type: str = Field(primary_key=True)  # "direct_input" | "pdf" | "chat_export" | "obsidian" | "markdown"
    weight: int = Field(default=5)               # 1-10; higher = more authoritative
```

### Table: `conflicts`

```python
# src/models/conflict.py
class ConflictStatus:
    PENDING = "pending"
    RESOLVED_ACCEPT_NEW = "resolved_accept_new"
    RESOLVED_KEEP_OLD = "resolved_keep_old"
    RESOLVED_CUSTOM = "resolved_custom"
    AUTO_RESOLVED = "auto_resolved"
    DISMISSED = "dismissed"

class Conflict(SQLModel, table=True):
    __tablename__ = "conflicts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")

    # The two conflicting memory IDs (Neo4j node IDs)
    incumbent_memory_id: str               # Older memory Neo4j node ID
    challenger_memory_id: str              # Newer memory Neo4j node ID

    # The source chunks
    incumbent_source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")
    challenger_source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")

    # Conflict metadata
    incumbent_content: str                 # Snapshot of incumbent text
    challenger_content: str                # Snapshot of challenger text
    ai_classification: str                 # "CONTRADICTION" | "UPDATE"
    ai_proposed_resolution: Optional[str] = None
    confidence_score: float                # 0.0-1.0

    # Resolution
    status: str = Field(default=ConflictStatus.PENDING, index=True)
    resolution_note: Optional[str] = None  # User's custom clarification text
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Table: `meta_documents`

```python
# src/models/meta_document.py
class MetaDocument(SQLModel, table=True):
    __tablename__ = "meta_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")
    title: str
    original_prompt: str
    parsed_intent: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    content_markdown: Optional[str] = None
    contributing_memory_ids: list[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )                                      # Neo4j Memory node IDs used in generation
    model_used: str = Field(default="claude-sonnet")
    credits_consumed: int = Field(default=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Table: `credit_transactions`

```python
# src/models/credit.py
class CreditTransaction(SQLModel, table=True):
    __tablename__ = "credit_transactions"

    id: int = Field(default=None, primary_key=True)  # BIGSERIAL
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    amount: int                            # Negative = deduction, positive = credit
    balance_after: int                     # Snapshot for auditability
    operation: str                         # "ingest_page" | "meta_doc_haiku" | "meta_doc_sonnet" | "top_up" | "signup_bonus"
    reference_id: Optional[uuid.UUID] = None  # source_id or meta_document_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Table: `arq_jobs` (managed by ARQ, not SQLModel)

ARQ creates its own job tracking in Redis. We mirror critical job state to PostgreSQL for the `/v1/ingest/status/{job_id}` endpoint:

```python
class JobStatus(SQLModel, table=True):
    __tablename__ = "job_statuses"

    id: str = Field(primary_key=True)      # ARQ job ID (str)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")
    job_type: str                          # "ingestion" | "graph" | "conflict" | "metadoc" | "deletion"
    status: str = Field(default="queued")  # "queued" | "active" | "completed" | "failed"
    progress_pct: int = Field(default=0)   # 0-100
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

## Neo4j Schema

### Node Labels & Properties

```cypher
// User — root tenant node
CREATE CONSTRAINT user_unique ON (u:User) ASSERT u.user_id IS UNIQUE;
(:User {
  user_id: "uuid",          // = Clerk user_id = PostgreSQL users.id
  email: "string",
  created_at: datetime()
})

// SystemProfile
CREATE CONSTRAINT profile_unique ON (p:SystemProfile) ASSERT p.profile_id IS UNIQUE;
(:SystemProfile {
  profile_id: "uuid",
  tenant_id: "uuid",        // ALWAYS present — used in every query
  name: "string",
  is_default: boolean
})

// Source
(:Source {
  source_id: "uuid",
  tenant_id: "uuid",
  original_filename: "string",
  file_type: "string",
  ingested_at: datetime()
})

// Memory — a single resolved, canonical fact
CREATE CONSTRAINT memory_unique ON (m:Memory) ASSERT m.memory_id IS UNIQUE;
(:Memory {
  memory_id: "uuid",
  tenant_id: "uuid",        // ALWAYS present
  content: "string",        // The actual fact text
  embedding_id: "string",   // Qdrant point ID
  created_at: datetime(),
  is_valid: boolean,        // false = superseded
  confidence: float         // 0.0-1.0
})

// Concept — extracted entity
CREATE INDEX concept_name_idx FOR (c:Concept) ON (c.name);
(:Concept {
  concept_id: "uuid",
  tenant_id: "uuid",
  name: "string",           // "React", "Neo4j", "Project Atlas"
  type: "string",           // "skill" | "tool" | "project" | "person" | "org" | "decision"
  first_seen: datetime(),
  last_seen: datetime()
})

// Conflict
(:Conflict {
  conflict_id: "uuid",
  tenant_id: "uuid",
  status: "string",
  classification: "string",
  confidence: float
})

// MetaDocument
(:MetaDocument {
  doc_id: "uuid",
  tenant_id: "uuid",
  title: "string",
  generated_at: datetime()
})
```

### Relationship Types

```cypher
// Ownership
(User)-[:HAS_PROFILE]->(SystemProfile)
(User)-[:HAS_SOURCE]->(Source)

// Memory connections
(SystemProfile)-[:HAS_MEMORY]->(Memory)
(Memory)-[:EXTRACTED_FROM {chunk_id: "string"}]->(Source)
(Memory)-[:RELATES_TO {weight: float, context: "string"}]->(Concept)

// Conflict graph
(Memory)-[:CONTRADICTS {conflict_id: "uuid", detected_at: datetime()}]->(Memory)
(Memory)-[:SUPERSEDES {resolved_at: datetime(), note: "string"}]->(Memory)

// MetaDocument
(MetaDocument)-[:CONTAINS {relevance_score: float}]->(Memory)
(User)-[:GENERATED]->(MetaDocument)

// Temporal
(Concept)-[:TEMPORAL_LINK {
  direction: "before" | "after",
  year: int,
  inferred: boolean
}]->(Concept)
```

### Key Cypher Queries (Reference)

```cypher
// Get all memories for a profile (for Meta-Document retrieval)
MATCH (u:User {user_id: $tenant_id})-[:HAS_PROFILE]->(p:SystemProfile {profile_id: $profile_id})
MATCH (p)-[:HAS_MEMORY]->(m:Memory)
WHERE m.is_valid = true
RETURN m ORDER BY m.created_at DESC

// Get concept neighborhood (for Graph Explorer node click)
MATCH (c:Concept {concept_id: $concept_id, tenant_id: $tenant_id})
MATCH (m:Memory)-[:RELATES_TO]->(c)
MATCH (m)-[:EXTRACTED_FROM]->(s:Source)
RETURN c, m, s LIMIT 50

// Find temporal chain for a concept
MATCH (c1:Concept {name: $concept_name, tenant_id: $tenant_id})
MATCH path = (c1)-[:TEMPORAL_LINK*1..5]->(c2:Concept)
RETURN path ORDER BY c2.first_seen
```

---

## Qdrant Collection Schema

```python
# Collection: "ravenbase_chunks"
# Created via: qdrant_client.recreate_collection(...)

CollectionConfig = {
    "collection_name": "ravenbase_chunks",
    "vectors_config": VectorParams(
        size=1536,                         # OpenAI text-embedding-3-small
        distance=Distance.COSINE
    ),
    "sparse_vectors_config": {
        "bm25": SparseVectorParams(        # For hybrid search (keyword)
            modifier=Modifier.IDF
        )
    }
}

# Every point payload:
Point = {
    "id": "uuid",                          # chunk_id
    "vector": [...],                       # 1536-dim embedding
    "payload": {
        "tenant_id": "uuid",               # ALWAYS present — used in every filter
        "source_id": "uuid",
        "profile_id": "uuid | null",
        "memory_id": "uuid | null",        # Linked Neo4j Memory node
        "content": "string",               # Original chunk text
        "chunk_index": int,
        "file_type": "string",
        "created_at": "ISO8601 string",
        "page_number": "int | null"
    }
}

# Standard search filter (ALWAYS include this in every Qdrant query):
TENANT_FILTER = {
    "must": [
        {"key": "tenant_id", "match": {"value": tenant_id}}
    ]
}
```

### Table: `chat_sessions`

```python
# src/models/chat_session.py
import uuid
from datetime import datetime, UTC
from typing import Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: uuid.UUID | None = Field(default=None, foreign_key="system_profiles.id")
    title: str | None = None               # auto-set from first 60 chars of first user message
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    # messages element format:
    # {"role": "user"|"assistant", "content": str, "created_at": "ISO8601"}
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

> **Tenant isolation:** All queries must filter `WHERE user_id = $tenant_id`.
> `messages` is stored as JSON (not JSONB) — sufficient for chat history.
> Only the last 6 messages are passed to the LLM in STORY-026 to cap prompt size.

---

## Performance: Required Composite Indexes

These indexes must be created in the initial Alembic migration (STORY-002).
Single-column indexes on `user_id` alone are insufficient for the query patterns
that list endpoints actually execute.

```sql
-- The three most critical composite indexes for query performance

-- 1. Source list: user's files sorted by date (used on every page load of /sources)
CREATE INDEX CONCURRENTLY idx_sources_user_created
  ON sources (user_id, created_at DESC);

-- 2. Conflict inbox: user's pending conflicts (polled frequently)
CREATE INDEX CONCURRENTLY idx_conflicts_user_status_created
  ON conflicts (user_id, status, created_at DESC);

-- 3. Chat session list: user's sessions newest-first
CREATE INDEX CONCURRENTLY idx_chat_sessions_user_updated
  ON chat_sessions (user_id, updated_at DESC);
```

**SQLModel equivalent** (in Alembic env.py, or via `__table_args__`):
```python
# src/models/source.py
class Source(SQLModel, table=True):
    __table_args__ = (
        Index("idx_sources_user_created", "user_id", "created_at"),
    )

# src/models/conflict.py
class Conflict(SQLModel, table=True):
    __table_args__ = (
        Index("idx_conflicts_user_status_created", "user_id", "status", "created_at"),
    )

# src/models/chat_session.py
class ChatSession(SQLModel, table=True):
    __table_args__ = (
        Index("idx_chat_sessions_user_updated", "user_id", "updated_at"),
    )
```

**Rule for agents:** Any model that will be queried with `WHERE user_id = X ORDER BY Y`
MUST have a composite index on `(user_id, Y)`. Never rely on the single-column `user_id`
index for sorted list queries.

---

## Alembic Migration Workflow

```bash
# Create a new migration (after changing SQLModel models):
uv run alembic revision --autogenerate -m "add source_authority_weights table"

# Apply migrations (dev):
uv run alembic upgrade head

# Apply migrations (production — via Railway deploy hook):
# See development/04-deployment.md

# Rollback one migration:
uv run alembic downgrade -1

# Never use:
# SQLModel.metadata.create_all(engine)   ← FORBIDDEN in production
```
