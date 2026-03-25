# PRD — 00. Executive Summary

> **Cross-references:** `prd/01-problem-statement.md` (market context) | `architecture/00-system-overview.md` (how)

---

## Vision

Ravenbase is an **immutable exocortex** — a Human-AI Long-Term Context Memory System that permanently captures, maps, and synthesizes a user's knowledge across years of scattered data, ensuring AI agents never lose context again.

**Core thesis:** The billion-dollar gap in the 2026 AI market is not intelligence — it is continuity. Every frontier model resets. Ravenbase does not.

---

## The Three Irreplaceable Differentiators

### 1. Deterministic Conflict Resolution (Memory Inbox)
When the system detects contradictory facts, it surfaces them to the user for explicit resolution rather than silently overwriting or probabilistically guessing. This is the **only system on the market** that treats user knowledge as immutable-until-explicitly-changed.

### 2. Hybrid Vector + Knowledge Graph Architecture
Qdrant handles semantic retrieval. Neo4j handles temporal, causal, and relational traversal. No existing consumer PKM tool combines both. This enables queries that pure vector systems cannot answer: "What led to my shift from React to Vue in 2023?"

### 3. Meta-Document Synthesis
The system traverses years of scattered context and synthesizes targeted, coherent outputs — a tailored resume, internship report, or project debrief — in seconds, by combining hybrid retrieval with frontier reasoning models.

---

## Platform Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────┐
│                    ravenbase.app                            │
│                                                             │
│  Landing Page → Auth/Onboarding → Dashboard                 │
│                                   ├── Graph Explorer        │
│                                   ├── Omnibar (input)       │
│                                   ├── Memory Inbox          │
│                                   └── Workstation (output)  │
└─────────────────────────────────────────────────────────────┘
                          │ REST API
┌─────────────────────────────────────────────────────────────┐
│                  api.ravenbase.app                          │
│             FastAPI (3-layer architecture)                  │
│                                                             │
│  Ingestion Service → ARQ Queue → Docling Workers            │
│  RAG Service → Qdrant (vectors) + Neo4j (graph)             │
│  Conflict Service → LLM Classification                      │
│  MetaDoc Service → Hybrid Retrieve + Synthesize             │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                           │
│  PostgreSQL (users, metadata) | Qdrant (embeddings)         │
│  Neo4j AuraDB (knowledge graph) | Supabase Storage (files)  │
└─────────────────────────────────────────────────────────────┘
```

---

## MVP Scope & Boundaries

### IN SCOPE (MVP)
- File ingestion: PDF, TXT, Markdown, ChatGPT JSON exports, Obsidian vault ZIPs
- Knowledge graph construction: entities, relationships, temporal links
- Memory Inbox: conflict detection + 3-flow resolution UI
- Meta-Document generation: resume, summary, report synthesis
- Graph Explorer: force-directed visualization, node detail panels
- System Profiles: scoped context switching (Work, Personal, Academic)
- Omnibar: slash-command interface + quick capture
- Auth: Clerk-based login/register + onboarding wizard
- Monetization: Free / Pro tiers with credit-pool system
- Landing page + pricing page

### OUT OF SCOPE (Post-MVP)
- Native mobile apps (web app must work on mobile Safari/Chrome)
- Browser extensions for real-time capture
- Real-time collaboration (multi-user graph sharing)
- Voice/audio ingestion
- Calendar / email integrations
- Public knowledge graph sharing

---

## Success Metrics (MVP)

| Metric | Target | Measurement |
|---|---|---|
| Beta users | 10 active within 30 days of launch | Clerk dashboard |
| p95 query latency | < 500ms | Grafana APM |
| Ingestion success rate | > 98% | ARQ job metrics |
| Conflict detection precision | > 85% | Manual spot-check on 50 samples |
| Meta-Doc generation time | < 30s (p95) | Grafana APM |
| Crash-free sessions | > 99.5% | Sentry |
| Landing page conversion | > 3% visitor → signup | Vercel Analytics |
| Lighthouse score (mobile) | > 90 | CI check |

---

## Development Context

- **Developer:** Natakorn Wannabovorn (Jedi) — solo development
- **Method:** BMAD story-driven agentic development with Claude Code
- **Course:** Agentic Development — Harbour.Space University, Bangkok
- **Timeline:** 10 sprints × 2 sprints/week = 5 weeks
- **Total stories:** 25 stories across 8 epics
- **Repos:** `ravenbase-api` (Python/FastAPI) + `ravenbase-web` (Next.js 15)

---

## Key Constraints

1. **Solo developer:** Every architecture decision must minimize operational complexity
2. **Budget:** Infrastructure must stay under $60/month during MVP
3. **Agentic workflow:** All code written by Claude Code agents; every decision must be explicit in docs
4. **Academic context:** Project must demonstrate mastery of agentic development methodology
5. **Production-grade:** Despite being a student project, code quality must meet production standards
