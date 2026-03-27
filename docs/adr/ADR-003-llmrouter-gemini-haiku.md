# ADR-003: LiteLLM router with Gemini Flash primary and Haiku fallback

**Status:** Accepted
**Date:** 2026-03-26
**Stories:** STORY-009

## Decision
Background LLM tasks (entity extraction, conflict classification,
NL→Cypher) route to Gemini 2.5 Flash as primary and Claude Haiku
as fallback via litellm.acompletion.

## Rationale
- Gemini Flash is cheaper and faster for high-volume background tasks
- Haiku fallback provides reliability when Gemini rate limits
- litellm unifies the interface — no provider-specific SDK calls
- lazy import of litellm (inside complete()) satisfies RULE 6

## Consequences
- litellm must be in pyproject.toml
- New LLM tasks must be added to _TASK_ROUTING in llm_router.py
- Never call provider SDKs directly — always go through LLMRouter
