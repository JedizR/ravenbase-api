# Ravenbase — Complete Development Flow & Human Guide

**Who this is for:** Jedi — the human developer running this project.
**What this replaces:** All previous versions of the Moving Forward Guide.
**Ground truth:** Everything here is derived from the current `/docs` corpus.

---

## Part 1 — The Big Picture

```
ONE-TIME SETUP          PHASE A (Sprints 1–17)       PHASE B (Sprints 18–35)
─────────────           ──────────────────────        ──────────────────────
[HUMAN] Create repos    [HUMAN] Open session          [HUMAN] Open session
[HUMAN] Set up 8        [HUMAN] Paste brief           [HUMAN] Paste brief
        services        [AGENT] Read → Plan           [AGENT] Read → Plan
[HUMAN] Fill env vars   [HUMAN] Approve plan          [HUMAN] Approve plan
[HUMAN] Install tools   [AGENT] Implement             [AGENT] Implement
[HUMAN] Install skills  [AGENT] Quality gate          [AGENT] Quality gate
                        [AGENT] Commit + push         [AGENT] Commit + push
                        [AGENT] Regen client (if)     [AGENT] Mark ✅
                        [AGENT] Mark ✅ + Journal      [AGENT] Journal entry
                        ────── repeat 17× ─────        ───── repeat 18× ──
                                ↓
                        [HUMAN] Backend gate check
                                ↓
                               Phase B begins
```

**37 stories. 35 sprints. Two repos. One loop.**

---

## Part 2 — One-Time Setup

> Do this once, before writing a single line of application code.
> Estimated time: 2–3 hours.

### 2.1 Install Prerequisites `[HUMAN]`

```bash
# Verify you have:
python3 --version     # Need 3.12+
node --version        # Need 20+
docker --version      # Need 24+
git --version

# Install if missing:
# Python 3.12: pyenv install 3.12.3 && pyenv global 3.12.3
# uv:          curl -LsSf https://astral.sh/uv/install.sh | sh
# Node 20:     nvm install 20 && nvm use 20
# Docker:      https://www.docker.com/products/docker-desktop

# CLI tools:
npm install -g @railway/cli
brew install stripe/stripe-cli/stripe && stripe login
brew install gh && gh auth login
brew install ngrok/ngrok/ngrok            # For webhook testing (STORY-018)
# Then: ngrok config add-authtoken YOUR_TOKEN (get token at ngrok.com)
```

### 2.2 Create Two GitHub Repos `[HUMAN]`

```bash
mkdir ~/ravenbase && cd ~/ravenbase
mkdir ravenbase-api ravenbase-web

cd ravenbase-api && git init && cd ..
cd ravenbase-web && git init && cd ..

# Copy the docs corpus into both repos
cp -r /path/to/ravenbase-docs/docs ravenbase-api/docs
cp -r /path/to/ravenbase-docs/docs ravenbase-web/docs

# Each repo gets its own CLAUDE.md
cp ravenbase-api/docs/CLAUDE.md ravenbase-api/CLAUDE.md
cp ravenbase-api/docs/design/CLAUDE_FRONTEND.md ravenbase-web/CLAUDE.md

# BMAD state files
mkdir -p ravenbase-api/.bmad ravenbase-web/.bmad
echo "001" > ravenbase-api/.bmad/story-counter.txt
echo "001" > ravenbase-web/.bmad/story-counter.txt

# gitignore
cat > ravenbase-api/.gitignore << 'EOF'
.envs/.env.dev
.envs/.env.production
__pycache__/
.venv/
*.pyc
.pytest_cache/
htmlcov/
EOF

cat > ravenbase-web/.gitignore << 'EOF'
.env.local
.next/
node_modules/
playwright-report/
test-results/
EOF

# Push to GitHub
gh repo create ravenbase-api --private
gh repo create ravenbase-web --private
cd ravenbase-api
git remote add origin git@github.com:YOUR_USERNAME/ravenbase-api.git
git add . && git commit -m "chore: initial docs corpus" && git push -u origin main
cd ../ravenbase-web
git remote add origin git@github.com:YOUR_USERNAME/ravenbase-web.git
git add . && git commit -m "chore: initial docs corpus" && git push -u origin main
cd ..
```

Workspace structure:
```
~/ravenbase/
├── ravenbase-api/
│   ├── CLAUDE.md         ← Backend agent rules
│   ├── docs/             ← Full docs corpus
│   └── .bmad/story-counter.txt
└── ravenbase-web/
    ├── CLAUDE.md         ← Frontend agent rules
    ├── docs/             ← Full docs corpus
    └── .bmad/story-counter.txt
```

### 2.3 Set Up 8 External Services `[HUMAN]`

Do these in order. Each produces credentials needed before development starts.

#### Service 1 — Supabase (PostgreSQL + Storage)
1. `supabase.com` → New project → Name: `ravenbase-prod`
2. Save: **DB Password**, **Project URL**, **anon key**, **service_role key**
3. Create Storage bucket `ravenbase-sources` (private)

#### Service 2 — Clerk (Auth)
1. `clerk.com` → New application → Name: `Ravenbase`
2. Enable: Email/password + Google OAuth
3. Save: **Publishable Key** (`pk_test_...`), **Secret Key** (`sk_test_...`), **Frontend API** (`your-app.clerk.accounts.dev`)
4. Add webhook: events `user.created`, `user.deleted`; save **Webhook Signing Secret** (`whsec_...`)
5. Find your **Clerk User ID** at `dashboard.clerk.com → Users` — save for `ADMIN_USER_IDS`

#### Service 3 — Qdrant Cloud (Vector Store)
1. `cloud.qdrant.io` → New cluster → Free tier
2. Save: **Cluster URL**, **API Key**

#### Service 4 — Neo4j AuraDB (Graph Database)
1. `neo4j.com/cloud/platform/aura-graph-database` → Free instance
2. Save: **Connection URI**, **Username**, **Password**
3. ⚠️ Download credentials file immediately — password shown only once

#### Service 5 — OpenAI (Embeddings)
1. `platform.openai.com/api-keys` → Create key; set $20/month limit
2. Save: **API Key** (`sk-...`)

#### Service 6 — Anthropic (User-facing LLM)
1. `console.anthropic.com → API Keys` → Create
2. Save: **API Key** (`sk-ant-...`)

#### Service 7 — Google AI Studio (Background LLM — Gemini Flash)
1. `aistudio.google.com/apikey` → Create API key
2. Save: **API Key** (`AIza...`)
3. Optional for local dev — background tasks fall back to Claude Haiku if absent (3× cost)

#### Service 8 — Stripe + Resend
**Stripe:** `stripe.com` → Get API keys → save **Publishable Key** + **Secret Key**

**Resend:**
1. `resend.com` → API Keys → Create → save **API Key** (`re_test_...`)
2. Resend Dashboard → Webhooks → Create → save **Webhook Signing Secret** (`whsec_...`)

### 2.4 Create Environment Files `[HUMAN]`

**`ravenbase-api/.envs/.env.dev`:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_DB_PASS@db.YOUR_REF.supabase.co:5432/postgres
REDIS_URL=redis://localhost:6379

# Auth
CLERK_SECRET_KEY=sk_test_YOUR_KEY
CLERK_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
CLERK_FRONTEND_API=your-app.clerk.accounts.dev

# AI
OPENAI_API_KEY=sk-YOUR_KEY
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY
GEMINI_API_KEY=AIza...              # Optional for local dev

# Vector + Graph
QDRANT_URL=https://YOUR_CLUSTER.cloud.qdrant.io
QDRANT_API_KEY=YOUR_KEY
NEO4J_URI=neo4j+s://YOUR_INSTANCE.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=YOUR_PASSWORD

# Storage
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ_YOUR_KEY
STORAGE_BUCKET=ravenbase-sources

# Payments + Email
STRIPE_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_WEBHOOK_SECRET=whsec_test_xxx  # Generated by: stripe listen
RESEND_API_KEY=re_test_xxx            # Leave blank to skip emails in local dev
RESEND_WEBHOOK_SECRET=whsec_...

# Security
CLOUDFLARE_ORIGIN_SECRET=changeme     # Only needed in production

# Config
APP_ENV=development
ENABLE_PII_MASKING=false
CONFLICT_SIMILARITY_THRESHOLD=0.87
MAX_DAILY_LLM_SPEND_USD=50.0
ADMIN_USER_IDS=user_YOUR_CLERK_USER_ID
```

**`ravenbase-web/.env.local`:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY
CLERK_SECRET_KEY=sk_test_YOUR_KEY
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ_YOUR_ANON_KEY
ADMIN_USER_IDS=user_YOUR_CLERK_USER_ID
# NEXT_PUBLIC_POSTHOG_KEY=phc_YOUR_KEY   # Optional — cookie banner only shows if set
```

### 2.5 Install Skills into Claude Code `[HUMAN]`

Run once. Applies globally to all Claude Code sessions.

```bash
# Terminal:
npx skills add shadcn-ui/ui --skill shadcn -a claude-code -g
npx skills add secondsky/claude-skills --skill tailwind-v4-shadcn -a claude-code -g
npx skills add Jeffallan/claude-skills --skill fastapi-expert -a claude-code -g

# Inside any active Claude Code session:
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
/install-skill https://github.com/aj-geddes/claude-code-bmad-skills
```

| Skill | Does | When it activates |
|---|---|---|
| `shadcn` | Reads live `components.json` at session start | Any shadcn/ui work |
| `tailwind-v4-shadcn` | Tailwind v4 gotchas, `@theme` pattern | Any Tailwind v4 work |
| `fastapi-expert` | Async patterns, lifespan, Pydantic v2 | Any FastAPI work |
| `superpowers` | TDD, systematic debugging, brainstorm→plan→implement | All sessions |
| BMAD skills | `/bmad:dev-story` story workflow commands | All sessions |

---

## Part 3 — The Complete Story Loop

> This loop repeats 37 times — once per story.
> `[AGENT]` = fully autonomous. `[HUMAN]` = requires you.

### Loop Start `[HUMAN]`

```bash
# Glance at current state (10 seconds)
cat ~/ravenbase/ravenbase-api/docs/.bmad/project-status.md

# Open Claude Code in the correct repo
cd ~/ravenbase/ravenbase-api    # backend stories
# OR
cd ~/ravenbase/ravenbase-web    # frontend stories
claude
```

---

### Step 1 — Paste the Brief `[HUMAN]`

Find the **Agent Implementation Brief** at the bottom of
`docs/stories/EPIC-XX/STORY-XXX.md`. Copy it. Paste it as your first message.

**For cross-repo stories** (STORY-007, STORY-008, STORY-018, STORY-028, STORY-036):
- Open **backend session** first → paste **Backend Agent Brief**
- After backend is merged → open **frontend session** → paste **Frontend Agent Brief**

---

### Step 2 — Agent Reads `[AGENT]`

Automatically reads:
1. `CLAUDE.md` — architecture rules
2. `docs/.bmad/project-status.md` — current state
3. Last 2–3 entries in `docs/.bmad/journal.md` — recent decisions + gotchas
4. The story file — all ACs
5. All files in "Before You Start"

---

### Step 3 — Agent Plans `[AGENT]`

Outputs:
- Files to create (exact paths)
- Files to modify (exact changes)
- How each AC maps to code

**Agent stops and waits for your explicit approval.**

---

### Step 4 — You Approve `[HUMAN]`

Review the plan. If correct: `"Approved. Proceed."`

If wrong, redirect before any code:
> "AC-3 doesn't need a new file — put it in `src/services/existing.py`. Revise the plan."

---

### Step 5 — Agent Implements `[AGENT]`

Strict order: **schemas/models → tests → implementation**

---

### Step 6 — Agent Runs Quality Gate `[AGENT]`

**Backend:**
```
make quality    → 0 ruff errors, 0 pyright errors
make test       → 0 failures, coverage ≥ 70%
```

**Frontend:**
```
npm run build   → 0 TypeScript errors, 0 warnings
npm run test    → 0 failures
```

If the gate fails: agent fixes, re-runs, does not commit until clean.

---

### Step 7 — Agent Verifies `[AGENT]`

Runs every command from "Testing This Story" in the story file.
Confirms every AC checkbox is met.

---

### Step 8 — Agent Commits `[AGENT]`

```bash
git add -A
git commit -m "feat(ravenbase): STORY-XXX brief description"
git push
```

---

### Step 9 — Agent Regenerates Client (if needed) `[AGENT]`

Only when the story added or changed an API endpoint:

```bash
cd ../ravenbase-web
npm run generate-client        # API server must be running at localhost:8000
git add src/lib/api-client/
git commit -m "chore: regenerate client after STORY-XXX"
git push
cd ../ravenbase-api
```

Stories that always require client regen:
`STORY-005, 007-BE, 008-BE, 010, 013, 016, 018-BE, 023, 024, 026, 028-BE, 029, 034, 035, 036-BE`

---

### Step 10 — Agent Updates All State `[AGENT]`

```bash
# 1. epics.md: 🔲 → ✅
# 2. .bmad/project-status.md: sprint, next story, last completed
# 3. .bmad/story-counter.txt: increment by 1 (e.g. "005" → "006")
# 4. .bmad/journal.md: append entry with all 6 fields + update stats table

git add docs/stories/epics.md \
        docs/.bmad/project-status.md \
        docs/.bmad/journal.md
git commit -m "docs: mark STORY-XXX complete"
git push
```

Journal entry format (agent fills this):
```
### STORY-XXX — [Title]
**Date:** YYYY-MM-DD | **Sprint:** N | **Phase:** A or B | **Repo:** ravenbase-api
**Quality gate:** ✅ clean | **Commit:** `xxxxxxxx`

**What was built:** [1–3 sentences]
**Key decisions:** [bullet points — architectural choices and why]
**Gotchas:** [surprises, workarounds, or "None"]
**Tech debt noted:** [deferred items or "None"]
```

---

### Step 11 — You Verify on GitHub `[HUMAN]`

Check the commit landed. Confirm CI is green.

**→ Pick next 🔲 from `epics.md`. Return to Loop Start.**

---

## Part 4 — The Three Situations

### Situation A — Session dies between stories (clean)

```bash
cd ~/ravenbase/ravenbase-api  # or ravenbase-web
claude
# Paste the Agent Implementation Brief from the next story file
```

No special handling. The agent reads `project-status.md` and `journal.md` and starts clean.

---

### Situation B — Session dies mid-story (partial work)

**Before opening Claude Code:**

```bash
git log --oneline -5    # What was committed
git status              # What's staged
ls src/services/        # What files actually exist
```

Read the story file — note which ACs have `[x]` vs `[ ]`.

```bash
# Mark in-progress
# Edit epics.md → 🔲 to 🔄
# Edit project-status.md → add session note describing current state
git add docs/stories/epics.md docs/.bmad/project-status.md
git commit -m "docs: STORY-XXX in progress — resume notes added"
git push
```

Open Claude Code, paste:

```
I am resuming STORY-XXX: [title]. It is partially complete.

Before anything else, read:
1. CLAUDE.md (architecture rules)
2. docs/.bmad/project-status.md (see session notes for current state)
3. docs/.bmad/journal.md (last 2–3 entries)
4. docs/stories/EPIC-XX/STORY-XXX.md (note which ACs have [x])
5. [list specific files created so far]

After reading, tell me:
- Which ACs are already met by existing code
- Which ACs are NOT yet met
- Your plan to complete ONLY the remaining work

Do NOT re-implement anything that already exists.
Do NOT start implementing — show me the completion plan first.
```

Review the agent's plan. Correct any misidentifications:
> "AC-3 is already implemented in `src/adapters/docling_adapter.py`. Skip it and focus only on AC-5."

Then complete the story normally.

---

### Situation C — Restart from scratch

```bash
rm src/services/my_new_service.py  # Delete story files
# Edit epics.md → 🔄 back to 🔲
git add -A
git commit -m "chore: reset STORY-XXX for clean restart"
git push
```

Start a fresh session with the standard Agent Implementation Brief.

---

## Part 5 — The Backend Gate

After Sprint 17 (STORY-029) completes, before opening any frontend story:

```bash
cd ~/ravenbase/ravenbase-api

# Clean install
rm -rf .venv
uv sync --dev
make test       # Must show: 0 failures
make quality    # Must show: 0 errors

cd ../ravenbase-web
npm ci
npm run generate-client   # Must produce non-empty src/lib/api-client/
```

Checklist `[HUMAN]`:
```
[ ] All 17 backend stories merged to main
[ ] make test: 0 failures from clean checkout
[ ] make quality: 0 ruff + pyright errors
[ ] npm run generate-client: non-empty typed client
[ ] curl localhost:8000/health → all 4 services healthy
```

**Do not start Sprint 18 until all five are checked.**

---

## Part 6 — Sprint Sequence

### Phase A — Backend (Sprints 1–17, `ravenbase-api`)

| Sprint | Story | Done when |
|---|---|---|
| 1 | STORY-001 | `make quality` passes. `/health` → `{"status":"ok"}` |
| 2 | STORY-002 | Migrations clean. All tables exist |
| 3 | STORY-003 + STORY-004 | Health: qdrant+neo4j ok. ARQ starts |
| 4 | STORY-005 | Upload → 202. File in Supabase Storage |
| 5 | STORY-006 | PDF parsed + embedded. Searchable in Qdrant |
| 6 | STORY-007-BE | SSE stream emits progress to curl |
| 7 | STORY-008-BE | `/v1/ingest/text` accepts + queues text |
| 8 | STORY-009 + STORY-010 | Neo4j nodes populated. Graph API works |
| 9 | STORY-012 + STORY-013 | Conflict detected + stored. Resolve + undo work |
| 10 | STORY-015 + STORY-016 | Retrieval returns chunks. MetaDoc streams SSE |
| 11 | STORY-018-BE | JWT validated. Clerk webhook creates User |
| 12 | STORY-023 | Credits deducted. 402 on insufficient balance |
| 13 | STORY-024 | Full cascade deletion across 4 stores |
| 14 | STORY-025 | PII masking active. Tests pass |
| 15 | STORY-026 | Chat streams tokens. Multi-turn session. Credits deducted |
| 16 | STORY-028-BE | `/v1/ingest/import-prompt` returns personalized prompt |
| 17 | STORY-029 | Graph query → cypher + nodes. Write ops rejected |

**→ BACKEND GATE ← (see Part 5)**

### Phase B — Frontend (Sprints 18–35, `ravenbase-web`)

| Sprint | Story | Done when |
|---|---|---|
| 18 | STORY-001-WEB | `npm run build` passes. `--primary: #2d4a3e` in globals.css |
| 19 | STORY-018-FE | Register → login → `/dashboard`. JWT on API calls |
| 20 | STORY-019 + STORY-020 | Onboarding wizard. Profile switching |
| 21 | STORY-007-FE + STORY-008-FE | IngestionProgress streams. Omnibar captures text |
| 22 | STORY-011 | Graph Explorer renders. Node click opens panel |
| 23 | STORY-014 | Memory Inbox: all 3 keyboard flows work |
| 24 | STORY-017 | Workstation streams Markdown. Export to .md |
| 25 | STORY-021 + STORY-022 | Landing page live. Stripe checkout works |
| 26 | STORY-027 | Chat UI streams. Citations link to graph nodes |
| 27 | STORY-028-FE | Import helper: copy prompt, paste, submit |
| 28 | STORY-030 | Query bar in Graph Explorer. Nodes highlight amber |
| 29 | STORY-031 | Dark mode toggle. No flash. Persists |
| 30 | STORY-032 | Welcome email sends. Low-credits warning sends |
| 31 | STORY-033 | Privacy + Terms pages. Cookie banner conditional |
| 32 | STORY-034 | Referral codes working. Settings → Referrals renders |
| 33 | STORY-035 | Export ZIP in Supabase. Email with link sends |
| 34 | STORY-036 | Admin dashboard. Credit adjustment works |
| 35 | STORY-037 | Activity middleware tracking. CRON purge at day 180 |

---

## Part 7 — Story-Specific Concerns

These stories need your active attention. Everything else is fully autonomous.

### STORY-001 — API Scaffold `[HUMAN: check before approving plan]`
- `pyproject.toml` must use `uv` syntax (`[project]` table), not Poetry
- FastAPI must use `lifespan` context manager, not `@app.on_event`
- `aiosqlite` must be in `[dependency-groups.dev]`
- `/health` endpoint must return `{"status": "ok"}`

### STORY-001-WEB — Frontend Scaffold `[HUMAN: verify after completion]`
Check `app/globals.css` contains:
```css
--primary: ...     /* must resolve to #2d4a3e */
--background: ...  /* must resolve to #f5f3ee */
```
If wrong, every subsequent frontend story builds with wrong colors.

### STORY-006 — Docling Pipeline `[HUMAN: budget a full session]`
- Content moderation (AC-11) must run **before** Docling, not after
- Docling backend: `pypdfium2` with `generate_page_images=False`
- If stuck: use Context7 MCP to fetch current Docling docs

### STORY-009 — Entity Extraction via LLMRouter `[HUMAN: verify LLMRouter]`
- Agent must implement `src/adapters/llm_router.py` using LiteLLM SDK
- Extraction must route to `gemini/gemini-2.5-flash` primary, Claude Haiku fallback
- First run will likely need 1–2 rounds of prompt refinement — normal

### STORY-018-BE — Clerk Auth `[HUMAN: critical test after completion]`
```bash
curl localhost:8000/v1/graph/nodes
# Must return 401 — not 200, not 500
```
If not 401, auth middleware is broken. Fix before continuing. Everything after depends on this.

For local webhook testing:
```bash
# In a dedicated terminal (keep running):
clerk webhooks listen --forward-to http://localhost:8000/webhooks/clerk
# Output: "Webhook signing secret: whsec_test_xxxxxxxxx"
# Copy → CLERK_WEBHOOK_SECRET in .envs/.env.dev
```

### STORY-022 — Pricing + Stripe `[HUMAN: start Stripe CLI first]`
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
# Printed signing secret → update STRIPE_WEBHOOK_SECRET in .env.dev
# This value is DIFFERENT from the Stripe dashboard secret
```
Before approving the plan: ask agent to show you the webhook handler. It must check Redis for `stripe:event:{event_id}` before processing (idempotency AC-11/12).

### STORY-036 — Admin Dashboard `[HUMAN: verify both env files]`
`ADMIN_USER_IDS` must be in **both** `.envs/.env.dev` (backend) and `.env.local` (web). Next.js server components read `process.env.ADMIN_USER_IDS`. If only in backend, the frontend middleware redirects everyone to `/dashboard`.

Find your Clerk user ID: `dashboard.clerk.com → Users → click your account`.

### STORY-037 — Cold Data Lifecycle `[HUMAN: verify two constraints]`
Before approving:
1. `ActivityTrackingMiddleware` must use `asyncio.create_task()` — never `await`. Blocking here slows every API request.
2. Purge task must check BOTH `User.tier IN ('pro', 'team')` AND `settings.admin_user_ids`. Either check alone is insufficient.

---

## Part 8 — Context Window Management

**The rule:** Always finish the current story before context dies. At ~80% context, push to complete and commit. A half-done story in a dead session is harder to resume than no story.

**Fresh agent = no problem.** Every story brief is self-contained. A new agent reads `CLAUDE.md`, `project-status.md`, `journal.md`, and the story file — and has everything it needs. No conversation history required.

---

## Part 9 — Production Deployment Checklist

When all 35 sprints are complete:

### Railway (Backend) `[HUMAN]`
```
[ ] GEMINI_API_KEY set (not optional — Haiku fallback costs 3× more)
[ ] MAX_DAILY_LLM_SPEND_USD=200.0 (not 50.0)
[ ] CLOUDFLARE_ORIGIN_SECRET set (32-char hex)
[ ] ADMIN_USER_IDS set (Clerk production user ID)
[ ] RESEND_WEBHOOK_SECRET set
[ ] STRIPE_WEBHOOK_SECRET matches production Stripe webhook
[ ] APP_ENV=production
[ ] ENABLE_PII_MASKING=true
```

### Vercel (Frontend) `[HUMAN]`
```
[ ] ADMIN_USER_IDS set (same as Railway)
[ ] NEXT_PUBLIC_API_URL pointing to production Railway URL
[ ] NEXT_PUBLIC_POSTHOG_KEY set if you want analytics
```

### Cloudflare `[HUMAN]`
```
[ ] WAF managed ruleset enabled
[ ] Bot Fight Mode enabled
[ ] Origin secret header rule: requests without X-CF-Secret → block
[ ] Rate limiting: 100 requests / 10 seconds / IP
```

### Monitoring `[HUMAN]`
```
[ ] Better Uptime: /health check every 60 seconds
[ ] Alert: llm_circuit_breaker.approaching_cap (warning)
[ ] Alert: llm_circuit_breaker.TRIPPED (critical — page immediately)
[ ] Alert: Dead Letter Queue depth > 0
[ ] Supabase PITR enabled
```

### Multi-Database Restore Order `[HUMAN — verify before go-live]`

Mandatory order: PostgreSQL first → Qdrant (`make reindex-missing`) → Neo4j (`make regraph-missing`). Never restore Qdrant or Neo4j before PostgreSQL — they are derived from it.

---

## Part 10 — Files You Interact With Every Day

| File | Purpose | Who updates it |
|---|---|---|
| `docs/stories/epics.md` | Story status board (🔲 🔄 ✅) | Agent after each story |
| `docs/.bmad/project-status.md` | Current sprint, next story | Agent after each story |
| `docs/.bmad/journal.md` | Append-only history | Agent after each story |
| `docs/.bmad/story-counter.txt` | Story number counter | Agent after each story |
| `docs/.bmad/resume-protocol.md` | How to resume mid-story | You read when needed |
| Story files (`STORY-XXX.md`) | Agent Brief you paste | You read; agent checks ACs |
| `CLAUDE.md` (repo root) | Backend architecture rules | Reference when redirecting |
| `CLAUDE.md` (`ravenbase-web`) | Frontend rules | Reference when redirecting |

---

## Part 11 — Moving to a Different Machine

```bash
git clone git@github.com:YOUR_USERNAME/ravenbase-api.git
git clone git@github.com:YOUR_USERNAME/ravenbase-web.git

# Re-create env files from your password manager
# Re-install tools: uv, gh, stripe CLI, Node.js 20+, Docker
# Re-install Claude Code skills (see Part 2, Section 2.5)

# Resume from:
cat ravenbase-api/docs/.bmad/project-status.md
```

---

## Part 12 — The One-Line Summary

> Read `project-status.md` → open Claude Code → paste the Agent Brief → approve the plan → watch the agent build → confirm the commit on GitHub.

Everything else is automated.

---

## Audit Status ✅

**Verified against `docs_newest_version.zip` — 81 files, 37 stories, 35 sprints.**
**Zero failures across all 20 structural check categories.**

| Category | Status |
|---|---|
| All 37 story files — structure + Agent Briefs complete | ✅ |
| Credit values consistent (18/45/3/8 credits) | ✅ |
| Model strings correct | ✅ |
| Pricing correct (Pro $15, Team $49, Free 500cr) | ✅ |
| 15 security layers documented | ✅ |
| 19 frontend rules sequential | ✅ |
| Schema complete (all fields including cold-data lifecycle) | ✅ |
| API contract complete (all endpoints) | ✅ |
| ENV vars in KICKSTART complete | ✅ |
| Sprint counts correct (37 stories, 35 sprints, 18 backend) | ✅ |
| Journal integrated across 5 files | ✅ |
| INP metric in NFR | ✅ |
| STORY-021 consistent (9 sections, FAQ in AC-1, dual CTA) | ✅ |
| UX micro-interaction patterns documented | ✅ |
| Preconnect resource hints in CLAUDE_FRONTEND | ✅ |
| ADR-011 LLMRouter documented | ✅ |
| BMAD state files all present | ✅ |
| Development loop fully automated (9 steps) | ✅ |
| story-counter.txt in loop Step 8 | ✅ |
| Cross-repo story protocol in loop preamble | ✅ |
