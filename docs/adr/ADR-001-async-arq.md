# ADR-001: Async-first architecture with ARQ and FastAPI lifespan

**Status:** Accepted
**Date:** 2026-03-25
**Stories:** STORY-001, STORY-004

## Decision
Use ARQ (async Redis queue) for all background processing.
Initialize ARQ pool in FastAPI lifespan context manager.
All DB and storage operations use async drivers (asyncpg, neo4j async).

## Rationale
- File parsing (Docling) and LLM calls are I/O-bound and slow
- HTTP endpoints must return 202 immediately and not block
- ASGITransport in tests does not trigger lifespan — tests must set
  app.state.arq_pool directly

## Consequences
- All worker tasks must not re-raise exceptions (prevents ARQ retry loops)
- Tests that use app.state must set it explicitly before requests
