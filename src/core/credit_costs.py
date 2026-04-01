# src/core/credit_costs.py
"""Canonical credit cost constants for all billable operations.

Single source of truth — import from here, never redefine locally.
"""

INGESTION_PER_PAGE: int = 1
"""Credits charged per page during document ingestion."""

META_DOC_HAIKU: int = 18
"""Credits for meta-document generation with Claude Haiku."""

META_DOC_SONNET: int = 45
"""Credits for meta-document generation with Claude Sonnet."""

CHAT_HAIKU: int = 3
"""Credits per chat turn with Claude Haiku."""

CHAT_SONNET: int = 8
"""Credits per chat turn with Claude Sonnet."""

NL_GRAPH_QUERY: int = 2
"""Credits per natural-language graph query."""

# Model-keyed lookup dicts for convenience
META_DOC_COSTS: dict[str, int] = {
    "claude-haiku-4-5-20251001": META_DOC_HAIKU,
    "claude-sonnet-4-6": META_DOC_SONNET,
}

CHAT_COSTS: dict[str, int] = {
    "claude-haiku-4-5-20251001": CHAT_HAIKU,
    "claude-sonnet-4-6": CHAT_SONNET,
}
