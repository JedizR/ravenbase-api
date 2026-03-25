# PRD — 01. Problem Statement & Market Context

> **Cross-references:** `prd/00-executive-summary.md` | `prd/02-personas.md`

---

## The Core Problem: AI Memory Does Not Work

In 2026, every frontier AI model suffers from one of three fundamental failure modes when it comes to long-term memory:

### Failure Mode 1: Probabilistic Amnesia (ChatGPT)
ChatGPT uses a continuous global memory model that autonomously decides what to retain. After 11+ days, users consistently report silent loss of nuanced professional preferences. The system makes probabilistic guesses when faced with contradictions — a behavior that is catastrophically unreliable for professional context management. There is no audit trail, no conflict notification, and no user control over what gets overwritten.

### Failure Mode 2: Context Siloization (Claude)
Claude's project-scoped architecture prevents context contamination but completely eliminates cross-domain synthesis. A software engineer cannot connect insights from their architecture project to their interview prep without manually copying context. The cognitive overhead of managing these boundaries negates the productivity gain entirely.

### Failure Mode 3: Structural Blindness (Mem.ai, Notion AI)
Pure vector similarity systems find semantically related text but cannot answer questions requiring temporal reasoning, causal relationships, or multi-hop graph traversal. "What was my tech stack in Q3 2023?" returns disconnected fragments. "What led to my career shift?" requires graph traversal that vector databases cannot perform.

---

## The Specific Pain Points (Validated by User Behavior)

| Pain Point | Evidence | Severity |
|---|---|---|
| "I repeat myself to AI every session" | Primary complaint across r/ChatGPT, r/ClaudeAI | Critical |
| "AI forgot what we agreed on last month" | 11-day memory loss study, Reddit r/ChatGPTPro | High |
| "I can't synthesize 3 years of notes into one document" | Graduate students, knowledge workers | High |
| "AI makes up relationships between my projects" | Mem.ai hallucination reports | Medium |
| "I lost context when switching tools" | Power users on r/PKMS | Medium |
| "I don't know what the AI knows about me" | ChatGPT memory opacity complaints | Medium |

---

## Competitor Feature Gap Matrix

| Capability | ChatGPT Plus | Claude Pro | Mem.ai | Notion AI | Ravenbase |
|---|---|---|---|---|---|
| **Cross-session memory** | Auto, unpredictable | Manual, siloed | Auto, hallucinates | None (30-day delete) | Permanent, graph-backed |
| **Conflict resolution** | Silent overwrite | None | Hallucinates | None | Manual Memory Inbox |
| **Temporal reasoning** | Weak | None | None | None | Neo4j graph traversal |
| **Multi-hop queries** | No | No | No | No | Cypher queries on Neo4j |
| **Synthesis output** | Ephemeral chat | Ephemeral chat | Ephemeral chat | Inline edits only | Exportable Meta-Docs |
| **Data ingestion** | Manual upload | Manual upload | Auto, disorganized | Manual paste | Docling + async queue |
| **Privacy/audit trail** | Opaque | Project-based | Cloud-only | Cloud-only | Full audit log + GDPR |
| **Context scoping** | Global (bleed risk) | Per-project | None | None | System Profiles |
| **Source attribution** | None | None | None | None | Every memory linked to source |

---

## Market Opportunity

The 2026 AI productivity market is bifurcating:
1. **Casual users** → Satisfied with ChatGPT/Claude ephemeral chat
2. **Power users (our market)** → Deeply frustrated with context loss, willing to pay for permanence

Target addressable market (initial): 500,000 power users globally who:
- Use AI > 3 hours/day
- Have been using AI tools for > 1 year
- Have experienced context loss with frustration
- Are technically literate enough to understand the value of knowledge graphs

---

## Why Now?

1. **Context window inflation has failed** — Gemini's 1M token window still suffers "brain fog" at scale; bigger is not better without structure
2. **Trust in AI memory is at an all-time low** — 2026 Reddit studies show widespread anxiety about AI forgetting/overwriting
3. **Knowledge workers are at scale** — The cohort of 3+ year AI users is now large enough to represent a serious TAM
4. **Graph databases are now accessible** — Neo4j AuraDB free tier, managed services make this architecture viable for a solo developer
