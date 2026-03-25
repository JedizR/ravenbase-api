# Development — 02. Coding Standards

> **Cross-references:** `docs/CLAUDE.md` (agent rules) | `development/00-project-structure.md`
>
> **Source:** Adapted from PROD_LV_DEV_FOR_SOLO_DEV_v4.md — Ravenbase specific patterns applied.

---

## The Three-Layer Architecture (Mandatory)

```
API Layer (FastAPI routes)
  → HTTP handling, auth, validation, rate limiting
  → NO business logic. NO direct DB/ML calls.
  → Routes are 20-40 lines maximum.

Service Layer (Python classes)
  → Business logic, orchestration, state management
  → NO HTTP (no Request, Response, HTTPException)
  → NO direct model/DB calls — always via adapters

Adapter Layer (thin wrappers)
  → One adapter, one external system
  → NO business logic. Swappable.
  → DoclingAdapter, QdrantAdapter, Neo4jAdapter, AnthropicAdapter
```

**Violation checklist — refuse to write these patterns:**

```python
# ❌ DB query inside a route handler
@router.post("/ingest")
async def ingest(file: UploadFile, session: Session = Depends(get_db)):
    source = session.exec(select(Source)...).first()  # ← VIOLATION

# ❌ Business logic inside an adapter
class QdrantAdapter:
    async def search(self, query, tenant_id):
        if len(query) < 3:  # ← VIOLATION: this is business logic
            return []

# ❌ HTTP request inside a service
class IngestionService:
    async def process(self, url: str):
        response = requests.get(url)  # ← VIOLATION
```

---

## Service Pattern

```python
# src/services/ingestion_service.py
from structlog import get_logger
from src.services.base import BaseService
from src.adapters.docling_adapter import DoclingAdapter
from src.schemas.ingest import ChunkResult

logger = get_logger()

class IngestionService(BaseService):
    """
    Handles document parsing and embedding generation.
    Adapter is injected for testability; created lazily in production.
    """

    def __init__(self, adapter: DoclingAdapter | None = None) -> None:
        self._adapter: DoclingAdapter | None = adapter

    def _get_adapter(self) -> DoclingAdapter:
        if self._adapter is None:
            self._adapter = DoclingAdapter()
        return self._adapter

    async def parse_and_chunk(
        self,
        content: bytes,
        filename: str,
        tenant_id: str,
        source_id: str,
    ) -> list[ChunkResult]:
        log = logger.bind(tenant_id=tenant_id, source_id=source_id, filename=filename)
        log.info("service.parse_and_chunk.started")

        try:
            chunks = await self._get_adapter().parse(content, filename)
            log.info("service.parse_and_chunk.done", chunk_count=len(chunks))
            return chunks
        except Exception as e:
            log.error("service.parse_and_chunk.failed", error=str(e))
            raise  # Let caller handle

    def cleanup(self) -> None:
        if self._adapter:
            self._adapter.cleanup()
```

---

## Adapter Pattern

```python
# src/adapters/base.py
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """
    All adapters extend this.
    __init__ must be fast — never load models or open connections here.
    Use lazy initialization (first method call triggers setup).
    """

    def cleanup(self) -> None:
        """Override to release connections, models, file handles."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()

# src/adapters/docling_adapter.py
from src.adapters.base import BaseAdapter

class DoclingAdapter(BaseAdapter):
    """Wraps Docling document parser. Heavy imports are lazy."""

    def __init__(self) -> None:
        self._converter = None  # Lazy init — __init__ must be fast

    def _get_converter(self):
        if self._converter is None:
            # Lazy import — Docling is heavy, don't load at module level
            from docling.document_converter import DocumentConverter  # noqa: PLC0415
            from docling.pipeline.standard_pdf_pipeline import PdfPipelineOptions  # noqa: PLC0415
            opts = PdfPipelineOptions(
                do_ocr=False,
                generate_page_images=False,    # Disable — not needed, saves CPU
                generate_picture_images=False,  # Disable
            )
            self._converter = DocumentConverter(pipeline_options=opts)
        return self._converter

    async def parse(self, content: bytes, filename: str) -> list[dict]:
        import asyncio  # noqa: PLC0415
        import tempfile
        import os

        # Docling is synchronous — run in thread pool to avoid blocking event loop
        loop = asyncio.get_running_loop()  # NOT get_event_loop() (deprecated)

        def _parse_sync():
            with tempfile.NamedTemporaryFile(suffix=f"_{filename}", delete=False) as f:
                f.write(content)
                tmp_path = f.name
            try:
                result = self._get_converter().convert(tmp_path)
                return result.document.export_to_dict()
            finally:
                os.unlink(tmp_path)

        return await loop.run_in_executor(None, _parse_sync)

    def cleanup(self) -> None:
        self._converter = None
```

---

## Error Handling Pattern

```python
# src/core/errors.py — centralized error codes
class ErrorCode:
    # Auth
    MISSING_AUTH = "MISSING_AUTH"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Resources
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    CONFLICT_NOT_FOUND = "CONFLICT_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"

    # Validation
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    DUPLICATE_SOURCE = "DUPLICATE_SOURCE"

    # Business
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"

    # System
    INGESTION_FAILED = "INGESTION_FAILED"
    DELETION_FAILED = "DELETION_FAILED"

# Pattern: never raise bare HTTPException with string message
# Always use error codes for frontend to handle programmatically

# ❌ WRONG
raise HTTPException(status_code=404, detail="Source not found")

# ✅ CORRECT
from src.core.errors import ErrorCode
raise HTTPException(status_code=404, detail={
    "code": ErrorCode.SOURCE_NOT_FOUND,
    "message": f"Source {source_id} not found or does not belong to this user"
})
```

---

## Logging Pattern (structlog)

```python
# src/core/logging.py
import structlog

def setup_logging(is_production: bool = False) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if is_production
            else structlog.dev.ConsoleRenderer(),
        ],
    )

# Usage pattern:
import structlog
logger = structlog.get_logger()

# ❌ WRONG
print(f"Processing file {filename}")

# ✅ CORRECT — bind context, use structured fields
log = logger.bind(tenant_id=tenant_id, source_id=source_id)
log.info("ingestion.started", filename=filename, size_bytes=len(content))
log.info("ingestion.completed", chunk_count=42, duration_ms=1240)
log.error("ingestion.failed", error=str(e), exc_info=True)
```

---

## Configuration Pattern (pydantic-settings)

```python
# src/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".envs/.env.dev",
        env_file_encoding="utf-8",
    )

    # Required secrets — Field(...) causes loud failure if missing
    DATABASE_URL: str
    REDIS_URL: str
    CLERK_SECRET_KEY: str
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    QDRANT_URL: str
    NEO4J_URI: str
    NEO4J_PASSWORD: str

    # Optional with defaults
    APP_ENV: str = "development"
    QDRANT_API_KEY: str | None = None
    NEO4J_USER: str = "neo4j"
    CONFLICT_SIMILARITY_THRESHOLD: float = 0.87
    MAX_CONCURRENT_INGEST_JOBS: int = 3
    ENABLE_PII_MASKING: bool = True
    SENTRY_DSN: str | None = None

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## Async Correctness

```python
# ❌ WRONG — deprecated in Python 3.10+
loop = asyncio.get_event_loop()
loop.run_until_complete(something())

# ✅ CORRECT
loop = asyncio.get_running_loop()
await loop.run_in_executor(None, sync_function)

# ❌ WRONG — blocking I/O in async context
async def embed(content: str) -> list[float]:
    import time
    time.sleep(1)  # ← blocks the event loop!

# ✅ CORRECT — use run_in_executor for sync I/O
async def embed(content: str) -> list[float]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_embed, content)
```

---

## Python Code Quality Standards

**Formatter + Linter:** Ruff (replaces Black + isort + flake8)
**Type checker:** Pyright (standard mode)
**Required:** Type hints on ALL function signatures

```python
# ✅ CORRECT — fully typed
async def process_document(
    content: bytes,
    filename: str,
    tenant_id: str,
    profile_id: str | None = None,
) -> list[ChunkResult]:
    ...

# ❌ WRONG — no types
async def process_document(content, filename, tenant_id, profile_id=None):
    ...
```

---

## TypeScript Code Quality Standards (Frontend)

- **Strict mode:** `"strict": true` in tsconfig.json
- **No `any`:** Use `unknown` and narrow types instead
- **Zod validation:** All data from the API must be validated with Zod schemas
- **No inline styles:** All styling via Tailwind utility classes
- **No magic strings:** Use constants or enums for status values

```typescript
// ✅ CORRECT — typed with Zod validation
import { z } from "zod";

const ConflictSchema = z.object({
  id: z.string().uuid(),
  status: z.enum(["pending", "resolved_accept_new", "resolved_keep_old", "resolved_custom"]),
  incumbent_content: z.string(),
  challenger_content: z.string(),
  confidence_score: z.number().min(0).max(1),
});

type Conflict = z.infer<typeof ConflictSchema>;
```

---

## Git Commit Convention

```
feat(story):     STORY-XXX: short description     ← new feature
fix(story):      STORY-XXX: short description     ← bug fix
chore:           regenerate API client from OpenAPI spec
test:            add integration test for cascade delete
docs:            update CLAUDE.md with new arch rules
refactor:        extract conflict detection to separate service
```

**Branch naming:** `feature/STORY-XXX-short-name`
**PR requirement:** CI must pass (make quality && make test)
