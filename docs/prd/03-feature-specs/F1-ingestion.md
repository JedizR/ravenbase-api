# Feature Spec — F1: Smart Ingestion Pipeline

> **Stories:** STORY-005, STORY-006, STORY-007, STORY-008

## Overview
Entry point for all user data. Accepts diverse input types, processes them asynchronously via ARQ workers, and deposits structured chunks into Qdrant + knowledge graph nodes into Neo4j.

## Supported Input Types
| Type | Extension | Parser | Notes |
|---|---|---|---|
| PDF | `.pdf` | Docling (pypdfium2) | Images disabled for speed |
| Plain text | `.txt` | Direct chunking | No parser overhead |
| Markdown | `.md` | Direct chunking | Preserve headings |
| ChatGPT export | `.json` | Custom parser | Extract conversation turns |
| Obsidian vault | `.zip` | Unzip + iterate `.md` files | Recursive |

## Acceptance Criteria
- [ ] File validated by magic bytes (not just MIME header)
- [ ] SHA-256 deduplication: same file for same user → return existing source_id
- [ ] Progress published via SSE at each stage: 0% → 30% → 70% → 100%
- [ ] 10-page PDF completes within 60s (no GPU)
- [ ] Corrupted file: source marked `failed`, no retry, no crash
- [ ] Source deletion cascades to all stores within 60s
