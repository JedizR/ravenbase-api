# Feature Spec — F4: Meta-Document Generator

> **Stories:** STORY-015, STORY-016, STORY-017

## Overview
Two-phase synthesis: (1) hybrid retrieval combining Qdrant semantic + Neo4j Cypher, (2) PII-masked generation via Claude Sonnet with streaming output.

## Intent Parsing
Input: `"Generate a 1-page resume tailored for a Senior Next.js Engineer role"`
Output:
```json
{
  "target_output": "resume",
  "key_concepts": ["Next.js", "TypeScript", "React", "Frontend Engineering"],
  "target_audience": "Technical hiring manager",
  "date_range": null,
  "max_length": "1 page"
}
```

## Retrieval Pipeline
1. Qdrant kNN search (top-30, tenant+profile filtered)
2. Neo4j Cypher traverse (temporal chains for key concepts)
3. Re-rank: `score = (semantic × 0.6) + (recency × 0.3) + (profile × 0.1)`
4. Dedup by content hash, return top-N

## Generation System Prompt
```
You are synthesizing a {target_output} for the user based on their actual history.

Rules:
- Write ONLY from the provided context. Never fabricate details.
- Format as Markdown with clear sections
- Use first-person voice ("Built X", "Led Y")
- If context is insufficient for a section, omit that section
- Target length: {max_length}
```

## Acceptance Criteria
- [ ] First token streams to client within 4s (p95)
- [ ] PII masking runs on all context before LLM call
- [ ] Contributing memory IDs saved + CONTAINS edges in Neo4j
- [ ] Export: MD download works, PDF uses browser print
- [ ] Insufficient credits → 402 before any LLM call (no waste)
- [ ] Generation timeout at 5 minutes with clean SSE error event
