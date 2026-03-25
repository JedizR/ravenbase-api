# PRD — 05. Monetization & Go-To-Market

---

## Pricing Tiers

| Tier | Price | Annual | Credits/mo | Key Limits | Target |
|---|---|---|---|---|---|
| **Free** | $0 | — | 500 | 10 source uploads, 10 Meta-Docs/mo, 3 profiles, **Haiku only** | Students, evaluators |
| **Pro** | $15/mo | $144/yr ($12/mo) | 2,000 | Unlimited uploads, unlimited Meta-Docs, 20 profiles, **Haiku + Sonnet** | Power users |
| **Team** | $49/mo | $468/yr ($39/mo) | 6,000 shared | Everything Pro + cross-user graph sharing (3 seats) | Small teams |

> **Pricing rationale:** Pro at $15/mo positions as an add-on to existing AI subscriptions
> (ChatGPT Plus/Claude Pro are $20/mo). The framing: "memory layer for your AI tools" —
> not a replacement. Free tier increased 200→500 credits, enabled by Gemini Flash cost
> reduction (~67% cheaper for background tasks).
>
> **Model access by tier:**
> - Free: Claude Haiku for generation (non-configurable)
> - Pro/Team: Choice of Claude Haiku or Claude Sonnet (configurable in Settings → AI Models)
> - Background tasks (extraction, classification, Cypher): always Gemini Flash regardless of tier

---

## Credit Consumption Table

| Operation | Credits | Notes |
|---|---|---|
| Text ingest (< 10KB) | 0 | Encourage daily capture habit |
| PDF ingest (per page) | 1 | OpenAI embeddings + Docling compute |
| Semantic search | 0 | Core utility — frictionless |
| NL graph query | 2 | LLM call (Gemini Flash) |
| Conflict classification | 0 | Absorbed into ingestion cost; Gemini Flash |
| Meta-Doc — Claude Haiku | **18** | ~3K tokens Haiku generation |
| Meta-Doc — Claude Sonnet | **45** | ~4K tokens Sonnet generation (Pro/Team only) |
| Chat message — Claude Haiku | **3** | Retrieval + ~500 token Haiku response |
| Chat message — Claude Sonnet | **8** | Retrieval + ~500 token Sonnet response (Pro/Team only) |
| Auto-conflict resolution | 0 | No LLM call |

> **These values are the single source of truth.** They supersede any other value in
> any story file. STORY-023, STORY-016, STORY-022, STORY-027 all reference this table.

---

## Credit Overage Handling

When a user exhausts their monthly credits:
1. Free tier: block Meta-Doc generation, show upgrade prompt
2. Pro tier: gracefully degrade — use Haiku instead of Sonnet for next 5 docs, then show top-up option
3. Top-up: purchase 500 credits for $5 (Stripe one-time payment)

---

---

## Annual Billing Discounts

| Tier | Monthly | Annual | Saving |
|---|---|---|---|
| Pro | $15/mo ($180/yr) | $144/yr ($12/mo) | $36/yr (2 months free) |
| Team | $49/mo ($588/yr) | $468/yr ($39/mo) | $120/yr |

---

## Referral Program

| Event | Referrer reward | Referee benefit |
|---|---|---|
| Signup via referral link | — | +200 bonus credits (700 total on first signup) |
| Referee's **first file upload** | +200 credits | — |

**Rules:**
- Reward triggers on first upload (not signup) — prevents fake account abuse
- Monthly cap: 50 referral rewards per user per month
- Referral credits work on Free tier; they do not unlock Pro model access
- Both accounts must be active (`User.is_active = True`)
- Referral code: first 8 chars of user UUID, uppercase (e.g., `550E8400`)
- Referral URL: `https://ravenbase.app/register?ref=550E8400`

---

## Go-To-Market Strategy

### Phase 1: Community-First (Months 1-2)

**Goal:** 100 engaged beta users from technical communities.

Target communities:
- `r/LocalLLaMA` — AI architecture nerds; share technical breakdown of hybrid vector+graph approach
- `r/PKMS` — knowledge management enthusiasts; frame as "AI that actually remembers"
- `r/PromptEngineering` — power users who understand context window frustration
- Hugging Face Discord, Langchain Discord — developer credibility

Content strategy:
- Technical teardown blog posts (build-in-public)
- Demo GIFs of Memory Inbox resolving a conflict
- Open-source the conflict detection algorithm

### Phase 2: Product Hunt Launch (Month 3)

**Positioning:** "Memory like a raven. Precision like a database. — powered by Knowledge Graphs, not probability"

**Launch requirements:**
- 50+ beta users ready to upvote on launch day
- Demo video showing: upload → conflict detection → Memory Inbox → resume generated in 30s
- Launch at 12:01 AM PST

**Launch day target:** Top 5 Product of the Day

### Phase 3: Influencer + SEO (Month 4+)

- Target "second brain" YouTube creators (Ali Abdaal-adjacent)
- SEO: "AI memory system", "ChatGPT memory alternative", "knowledge graph PKM"
- Affiliate program: 20% revenue share for first 12 months per referred Pro subscriber
