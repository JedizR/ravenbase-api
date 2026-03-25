# PRD — 04. Non-Functional Requirements

> **Cross-references:** `architecture/05-security-privacy.md` | `development/05-operations.md`

---

## Performance SLAs

| Operation | p50 | p95 | Hard Limit | How Measured |
|---|---|---|---|---|
| Omnibar text ingest (< 1KB) | < 1s | < 3s | 5s | Job queued + indexed |
| Semantic search query | < 200ms | < 500ms | 1s | API response time |
| Meta-Document first token | < 2s | < 4s | 8s | SSE: time to first `data:` |
| PDF ingestion — 10 pages | < 30s | < 60s | 120s | source.status = completed |
| PDF ingestion — 50 pages | < 90s | < 180s | 300s | source.status = completed |
| Conflict detection | < 30s | < 60s | 120s | Conflict record created |
| Memory Inbox triage (UI) | < 100ms | < 200ms | 500ms | Optimistic UI update |
| Graph Explorer render | < 1.5s | < 2.5s | 5s | All nodes painted |
| GDPR deletion cascade | < 30s | < 60s | 120s | All stores purged |
| Page load (landing, LCP) | < 1.5s | < 2.5s | — | Lighthouse |
| INP (Interaction to Next Paint) | < 100ms | < 200ms | — | Chrome DevTools → Performance panel; Google `web-vitals` library |

---

## Availability

- Target uptime: **99.5%** (allows ~22h downtime/month) — appropriate for MVP
- Health endpoint monitored every 60 seconds (Better Uptime free tier)
- Alert: PagerDuty-style notification via email if health returns 503 for > 2 minutes

---

## Security Requirements

| Requirement | Standard |
|---|---|
| Auth on all API endpoints | Clerk JWT, validated per-request |
| Tenant isolation | Qdrant filter + Neo4j WHERE + PostgreSQL RLS |
| Encryption in transit | TLS 1.3 (Railway + Vercel enforced) |
| Encryption at rest | AES-256 (Supabase, Qdrant Cloud, Neo4j AuraDB) |
| PII masking | Presidio before all external LLM calls |
| Rate limiting | IP-level (Railway) + per-user Redis sliding window |
| CORS | Restricted to `ravenbase.app` in production |
| Input validation | MIME + magic bytes + size limits |
| SQL injection | ORM + parameterized queries only |
| GDPR Right to Erasure | Full cascade within 60 seconds |

---

## Scalability Targets (MVP + Near-Term)

| Metric | MVP Target | 6-month Target |
|---|---|---|
| Concurrent users | 50 | 500 |
| Documents per user | 100 | 1,000 |
| Chunks in Qdrant | 500K total | 5M total |
| Neo4j nodes | 50K (AuraDB Free limit) | 500K (AuraDB Pro) |
| API requests/hour | 1,000 | 50,000 |

---

## Reliability Requirements

| Requirement | Implementation |
|---|---|
| No dropped jobs on worker restart | ARQ SIGTERM handler; re-enqueue if interrupted |
| No data loss on API crash | All mutations committed before queue enqueue |
| Failed jobs retried | max_tries=3 with exponential backoff |
| Permanent failures isolated | Dead Letter Queue in Redis, alert if depth > 0 |
| Database: point-in-time recovery | Supabase PITR enabled (7-day window) |
| Automated backups | Supabase daily backup + Qdrant snapshot weekly |

---

## Compliance

| Requirement | Status |
|---|---|
| GDPR Right to Erasure | Full cascade implementation (STORY-024) |
| GDPR Right of Access | Implemented via `GET /v1/export/my-data` (post-MVP) |
| CCPA | Delete endpoint covers California requirements |
| Vector embeddings treated as PII | Included in deletion cascade |
| Data Processing Agreement | Required with Supabase, OpenAI, Anthropic |
| Privacy Policy | Required before launch; disclose LLM API usage |
