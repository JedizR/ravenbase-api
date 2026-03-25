# Architecture — 00. System Overview

> **Cross-references:** `architecture/01-tech-stack-decisions.md` | `development/00-project-structure.md`
>
> **AGENT NOTE:** Read this before implementing any story. This is the source of truth for system boundaries.

---

## Repository Structure

Ravenbase uses **two separate repositories** (per BMAD solo dev blueprint — different deployment targets, different toolchains):

```
ravenbase-api/      ← Python FastAPI backend (Railway)
ravenbase-web/      ← Next.js 15 frontend (Vercel)
workspace/            ← Parent directory (local only)
└── docker-compose.local.yml   ← Ties both together for local dev
```

---

## Service Map

```
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND (ravenbase-web)                    │
│              Next.js 15 App Router — Vercel Deploy              │
│                                                                 │
│  (marketing)/  → Landing page (light mode, framer-motion)       │
│  (auth)/       → Clerk login/register/onboarding                │
│  (dashboard)/  → Core app (dark mode)                           │
│    ├── graph/        Graph Explorer (Cytoscape.js)              │
│    ├── inbox/        Memory Inbox (keyboard-first)              │
│    ├── workstation/  Meta-Document editor (streaming)           │
│    └── settings/     Profiles, sources, account                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS REST + SSE
                            │ Auth: Clerk JWT (Bearer token)
                            │ Client: Auto-generated from OpenAPI
┌───────────────────────────▼─────────────────────────────────────┐
│                    BACKEND (ravenbase-api)                     │
│              FastAPI — Railway — api.ravenbase.app            │
│                                                                 │
│  /v1/ingest/*   → upload, text, status, SSE progress           │
│  /v1/search     → hybrid semantic + keyword search              │
│  /v1/conflicts/* → list, resolve, undo                         │
│  /v1/graph/*    → node data for visualization                   │
│  /v1/metadoc/*  → generate (streaming SSE), list, export       │
│  /v1/profiles/* → CRUD for System Profiles                     │
│  /v1/sources/*  → list, delete (cascade)                       │
│  /health        → DB + Redis + Qdrant + Neo4j checks           │
└────────────────┬────────────────────────────────────────────────┘
                 │ enqueues to ARQ
┌────────────────▼────────────────────────────────────────────────┐
│                    ARQ WORKERS (Python async)                    │
│              Separate Railway worker dyno                        │
│                                                                 │
│  ingestion_worker  → Docling → chunk → embed → Qdrant          │
│  graph_worker      → entity extract → write Neo4j              │
│  conflict_worker   → similarity scan → LLM classify            │
│  deletion_worker   → cascade delete (Storage+Qdrant+Neo4j+PG)  │
│  metadoc_worker    → hybrid retrieve → PII mask → LLM stream   │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                      STORAGE LAYER                               │
│  PostgreSQL (Supabase)  → users, sources, profiles, conflicts   │
│  Redis (Railway)        → ARQ queue, rate limiting, SSE pub/sub │
│  Qdrant                 → vector embeddings (1536-dim)          │
│  Neo4j AuraDB           → knowledge graph (nodes + edges)      │
│  Supabase Storage       → raw uploaded files (S3-compatible)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Multi-Tenancy Enforcement

Every piece of data carries `tenant_id` (= Clerk `user_id`, UUID):

```
PostgreSQL:  WHERE user_id = {tenant_id}             (RLS + explicit filter)
Qdrant:      filter: must: [key: "tenant_id", match: tenant_id]
Neo4j:       WHERE m.tenant_id = $tenant_id          (every Cypher query)
Storage:     Path /{tenant_id}/{source_id}/{filename}
```

**Rule:** `tenant_id` is passed explicitly from route → service → adapter.  
**Never** infer tenant from session state inside an adapter.

---

## Data Flow: File Ingestion (End-to-End)

```
1. User drops PDF in UI
2. POST /v1/ingest/upload
   → MIME + magic bytes validation
   → store raw file → Supabase Storage
   → INSERT sources (status=pending)
   → enqueue ingestion_job → ARQ
   → return {job_id}

3. ARQ: ingestion_worker
   → fetch file from storage
   → Docling parse (pypdfium2 backend, images OFF)
   → chunk text (512 tokens, 50 overlap, with metadata)
   → OpenAI embed (batch, text-embedding-3-small)
   → upsert → Qdrant (tenant_id, source_id, chunk_id, created_at)
   → UPDATE sources status=indexing
   → enqueue graph_job

4. ARQ: graph_worker
   → Claude Haiku: extract entities (structured JSON)
   → write Concept + Memory nodes → Neo4j
   → write EXTRACTED_FROM, RELATES_TO edges
   → UPDATE sources status=completed
   → enqueue conflict_job

5. ARQ: conflict_worker
   → Qdrant: cosine similarity scan (threshold: 0.87, new vs existing memories)
   → candidate pairs → Claude Haiku classify [CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE]
   → CONTRADICTION/UPDATE → INSERT conflicts table + CONTRADICTS Neo4j edge
   → notify via Redis pub/sub → SSE to subscribed clients
```

---

## Data Flow: Meta-Document Generation

```
1. User submits prompt in Workstation
2. POST /v1/metadoc/generate
   → enqueue metadoc_job → ARQ
   → open SSE stream (EventSourceResponse)

3. ARQ: metadoc_worker
   → Phase 1: Claude Haiku parse intent
               → {target_role, key_concepts[], date_range, max_length}
   → Phase 2: Qdrant kNN search (tenant+profile scoped)
   → Phase 3: Neo4j Cypher traversal (temporal + relational)
   → Phase 4: re-rank (relevance × recency × profile_weight)
   → Phase 5: Presidio PII masking
   → Phase 6: stream Claude Sonnet synthesis → SSE
   → INSERT meta_documents + CONTAINS edges in Neo4j
```

---

## Environment Tiers

| Tier | API Host | Database | Notes |
|---|---|---|---|
| Local | localhost:8000 | Docker (PG+Redis), Qdrant Docker, Neo4j AuraDB Free | `make local-up` |
| Staging | Railway preview URL | Supabase staging project | Auto-deploy on PR |
| Production | api.ravenbase.app | Supabase prod project | Auto-deploy on merge to main |

---

## Estimated Monthly Infrastructure Cost (MVP)

| Service | Cost |
|---|---|
| Railway (API + Worker dyno) | ~$20/mo |
| Supabase Pro (PG + Storage) | $25/mo |
| Qdrant Cloud Free | $0 |
| Neo4j AuraDB Free | $0 |
| OpenAI embeddings (MVP scale) | ~$5/mo |
| Anthropic API (MVP scale) | ~$10/mo |
| Vercel (frontend) | $0 |
| **Total** | **~$60/mo** |
