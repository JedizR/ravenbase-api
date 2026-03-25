# Kickstart Guide — From Zero to First Working Story

> **This guide takes you from a folder of docs to a running development machine with Claude Code executing stories.**
> Read this once completely before doing anything. It will save you hours.

---

## Prerequisites — Install These First (One Time)

```bash
# Check what you have:
python3 --version     # Need 3.12+
node --version        # Need 20+
docker --version      # Need 24+
git --version         # Any recent version

# Install missing tools:
# Python 3.12:  pyenv install 3.12.3 && pyenv global 3.12.3
# uv:           curl -LsSf https://astral.sh/uv/install.sh | sh
# Node 20:      nvm install 20 && nvm use 20
# Docker:       https://www.docker.com/products/docker-desktop

# Install Railway CLI (for deployment later):
npm install -g @railway/cli

# Stripe CLI (needed for STORY-022 webhook testing):
brew install stripe/stripe-cli/stripe
# Then authenticate:
stripe login

# Install BMAD skills into Claude Code (critical for story workflow):
# → Open Claude Code in any folder
# → Run: /install-skill https://github.com/aj-geddes/claude-code-bmad-skills
# → This installs /bmad:dev-story and related commands
```

---

## Phase 1 — Create Your Two Repos (Do This Once)

```bash
# Create a workspace folder (parent of both repos)
mkdir ~/ravenbase && cd ~/ravenbase

# Create the two repos
mkdir ravenbase-api
mkdir ravenbase-web
cd ravenbase-api && git init && cd ..
cd ravenbase-web && git init && cd ..

# Copy docs into both repos
cp -r /path/to/ravenbase-docs/docs ravenbase-api/docs
cp -r /path/to/ravenbase-docs/docs ravenbase-web/docs

# Set up the .bmad story counter in each repo
mkdir -p ravenbase-api/.bmad ravenbase-web/.bmad
echo "001" > ravenbase-api/.bmad/story-counter.txt
echo "001" > ravenbase-web/.bmad/story-counter.txt

# Create the CLAUDE.md files (each repo needs its own)
cp ravenbase-api/docs/CLAUDE.md ravenbase-api/CLAUDE.md
cp ravenbase-api/docs/design/CLAUDE_FRONTEND.md ravenbase-web/CLAUDE.md

# Create GitHub repos and push
gh repo create ravenbase-api --private
gh repo create ravenbase-web --private
cd ravenbase-api && git remote add origin git@github.com:YOUR_USERNAME/ravenbase-api.git && cd ..
cd ravenbase-web && git remote add origin git@github.com:YOUR_USERNAME/ravenbase-web.git && cd ..
```

Your workspace now looks like:
```
~/ravenbase/
├── ravenbase-api/
│   ├── CLAUDE.md         ← Backend agent rules
│   ├── docs/             ← Full docs corpus
│   └── .bmad/
│       └── story-counter.txt
└── ravenbase-web/
    ├── CLAUDE.md         ← Frontend agent rules (from design/CLAUDE_FRONTEND.md)
    ├── docs/             ← Full docs corpus (same copy)
    └── .bmad/
        └── story-counter.txt
```

---

## Phase 2 — Set Up External Services (One Time, ~45 min)

Do these in order. Each one produces secrets you'll need for `.env`.

### Step 1: Supabase (PostgreSQL + Storage)
1. Go to https://supabase.com → New project → Name: `ravenbase-prod`
2. Save: **Database Password**, **Project URL**, **anon key**, **service_role key**
3. Create a storage bucket named `ravenbase-sources` (set to private)
4. Enable Row Level Security on all tables (you'll create via Alembic, but enable RLS now)

### Step 2: Clerk (Auth)
1. Go to https://clerk.com → New application → Name: `Ravenbase`
2. Enable: Email/password + Google OAuth
3. Save: **Publishable Key** (`pk_test_...`), **Secret Key** (`sk_test_...`)
4. Add webhook: URL = `https://api.ravenbase.app/webhooks/clerk` (use Clerk CLI or ngrok for local dev — see below)
5. Save: **Webhook Signing Secret** (`whsec_...`)

**Testing webhooks locally — use Clerk CLI (preferred):**

```bash
# Clerk CLI forwards webhooks from Clerk's servers to your local machine.
# No public URL needed.
npm install -g @clerk/clerk-cli

# In a dedicated terminal (keep running during STORY-018 development):
clerk webhooks listen --forward-to http://localhost:8000/webhooks/clerk

# Output will show: "Webhook signing secret: whsec_test_xxxxxxxxx"
# Copy this → set as CLERK_WEBHOOK_SECRET in .envs/.env.dev
```

**Alternative: ngrok (if Clerk CLI doesn't work):**
```bash
# Install: https://ngrok.com/download
ngrok http 8000
# Prints: https://abc123.ngrok.io → http://localhost:8000

# In Clerk dashboard → Webhooks → Add endpoint:
# URL: https://abc123.ngrok.io/webhooks/clerk
# Events: user.created, user.deleted
# Copy the signing secret → CLERK_WEBHOOK_SECRET in .env.dev
```

**What triggers during STORY-018 testing:**
```bash
# After running Clerk CLI or ngrok, trigger a test event:
# → Go to Clerk dashboard → Webhooks → your endpoint → Send test event
# → Or create a real test user at localhost:3000/register
# → Check terminal: should see "user.created event processed"
# → Check DB: SELECT * FROM users; — should show 1 row
```

### Step 3: Qdrant Cloud (Vector Store)
1. Go to https://cloud.qdrant.io → New cluster → Free tier
2. Save: **Cluster URL**, **API Key**
3. Note: Free tier = 1GB storage. Sufficient for the entire MVP and beta.

### Step 4: Neo4j AuraDB (Graph Database)
1. Go to https://neo4j.com/cloud/platform/aura-graph-database → Free instance
2. Save: **Connection URI** (`neo4j+s://xxxxx.databases.neo4j.io`), **Username**, **Password**
3. Download the credentials file — password is only shown once

### Step 5: OpenAI API Key
1. Go to https://platform.openai.com/api-keys → Create key
2. Set a usage limit of $20/month to prevent surprises
3. Save: **API Key** (`sk-...`)

### Step 6: Anthropic API Key
1. Go to https://console.anthropic.com → API Keys → Create
2. Save: **API Key** (`sk-ant-...`)

### Step 7: Create `.envs/.env.dev` in the API repo

```bash
cat > ~/ravenbase/ravenbase-api/.envs/.env.dev << 'EOF'
# ── Database
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SUPABASE_DB_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# ── Redis (local Docker for dev)
REDIS_URL=redis://localhost:6379

# ── Auth
CLERK_SECRET_KEY=sk_test_YOUR_KEY
CLERK_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
CLERK_FRONTEND_API=your-app.clerk.accounts.dev  # Found in Clerk Dashboard → API Keys

# ── AI
OPENAI_API_KEY=sk-YOUR_KEY
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY

# ── Vector Store
QDRANT_URL=https://YOUR_CLUSTER.cloud.qdrant.io
QDRANT_API_KEY=YOUR_QDRANT_API_KEY

# ── Graph Database
NEO4J_URI=neo4j+s://YOUR_INSTANCE.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD

# ── File Storage
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ_YOUR_SERVICE_ROLE_KEY
STORAGE_BUCKET=ravenbase-sources

# ── Stripe (used in STORY-022)
STRIPE_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_WEBHOOK_SECRET=whsec_test_xxxxxxxxxxxxx  # Generated by stripe listen for local dev
RESEND_API_KEY=re_test_xxxxxxxxxxxx  # Get from resend.com/api-keys — leave blank to skip email in local dev
RESEND_WEBHOOK_SECRET=whsec_...    # Resend Dashboard → Webhooks → Signing Secret

CLOUDFLARE_ORIGIN_SECRET=changeme-replace-with-32-char-hex-in-production  # See architecture/05-security-privacy.md Layer 7

# ── Config
APP_ENV=development
ENABLE_PII_MASKING=false
CONFLICT_SIMILARITY_THRESHOLD=0.87
MAX_CONCURRENT_INGEST_JOBS=3
GEMINI_API_KEY=AIza...              # Google AI Studio: aistudio.google.com/apikey — optional for local dev
MAX_DAILY_LLM_SPEND_USD=50.0        # Hard daily cap on LLM API spend (Layer 14); set 200.0 in production
ADMIN_USER_IDS=user_xxx             # Comma-separated Clerk user IDs with admin access
                                     # Find at: dashboard.clerk.com → Users → click your account → User ID
EOF

# Never commit this file:
echo ".envs/.env.dev" >> ~/ravenbase/ravenbase-api/.gitignore
echo ".envs/.env.production" >> ~/ravenbase/ravenbase-api/.gitignore
```

**Local webhook testing for Stripe (needed for STORY-022):**
```bash
# Forward Stripe webhooks to your local server:
stripe listen --forward-to localhost:8000/webhooks/stripe

# This outputs a webhook signing secret for local use:
# > Ready! Your webhook signing secret is whsec_test_xxxxxxxxxxxxx
# Add this to .envs/.env.dev as: STRIPE_WEBHOOK_SECRET=whsec_test_xxxxxxxxxxxxx
```

### Step 8: Create `.env.local` in the web repo

```bash
cat > ~/ravenbase/ravenbase-web/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY
CLERK_SECRET_KEY=sk_test_YOUR_KEY
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ_YOUR_ANON_KEY
ADMIN_USER_IDS=user_xxx                # Your Clerk user ID — find at dashboard.clerk.com → Users
EOF

echo ".env.local" >> ~/ravenbase/ravenbase-web/.gitignore
```

---

## Phase 3 — Open Claude Code Sessions

### Opening a session (backend)

```bash
cd ~/ravenbase/ravenbase-api
claude  # Opens Claude Code in this folder
```

### Opening a session (frontend)

```bash
cd ~/ravenbase/ravenbase-web
claude  # Opens Claude Code in this folder
```

You can run both terminals simultaneously. Each Claude Code session only sees its own repo.

---

## Phase 4 — The BMAD Story Execution Loop

This is the repeating pattern for every single story. Internalize it.

```
┌─────────────────────────────────────────────────────────────┐
│                THE STORY EXECUTION LOOP                     │
│                                                             │
│  1. Pick next story from docs/stories/epics.md              │
│     (Check status column: 🔲 = ready to start)              │
│                                                             │
│  2. Open Claude Code in the correct repo                    │
│     Backend story → ravenbase-api/                          │
│     Frontend story → ravenbase-web/                         │
│                                                             │
│  3. Paste the story prompt (see templates below)            │
│                                                             │
│  4. REVIEW THE PLAN — don't approve blindly                 │
│     - Does it follow 3-layer architecture?                  │
│     - Are all acceptance criteria covered?                  │
│     - Are there unexpected new dependencies?                │
│                                                             │
│  5. Approve: "Looks good, implement it"                     │
│                                                             │
│  6. Watch the implementation                                │
│     - Intervene if agent breaks architecture rules          │
│     - Use CLAUDE.md rules to redirect: "Per CLAUDE.md..."   │
│                                                             │
│  7. Quality gate (run these yourself in terminal)           │
│     make quality && make test    (backend)                  │
│     npm run build && npm run test (frontend)                │
│                                                             │
│  8. Mark story complete                                     │
│     - Update ACs in story file: - [ ] → - [x]               │
│     - Update epics.md: 🔲 → ✅                               │
│     - Increment .bmad/story-counter.txt                     │
│                                                             │
│  9. Commit + PR + Merge                                     │
│     git add -A                                              │
│     git commit -m "feat(story): STORY-XXX description"      │
│     gh pr create && gh pr merge                             │
│                                                             │
│  10. If backend story completed endpoints:                  │
│      → Run in web repo: npm run generate-client             │
│      → Commit the regenerated client                        │
│                                                             │
│  → Return to step 1                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 5 — Starting a Story Session

Copy the "Agent Implementation Brief" (or "Backend Agent Brief" / "Frontend Agent Brief" for split stories) from the bottom of the story file.
That is your entire opening message to Claude Code.

The Brief already contains:
- Which files to read before starting
- The key constraints
- The "Show plan first" instruction

You do not need to add anything. The Brief is self-contained.

For multi-repo stories (STORY-007, STORY-018): use the "Backend Agent Brief" in the
backend session and the "Frontend Agent Brief" in the frontend session.

---

## Phase 5 (Legacy) — Story Prompt Templates

These templates are for reference. Prefer using the Agent Implementation Brief directly from the story file.

### Backend Story Prompt (for `ravenbase-api/`)

```
I need you to implement STORY-XXX.

Before starting, read these files completely:
1. CLAUDE.md  (architecture rules — these are mandatory)
2. docs/stories/EPIC-XX-name/STORY-XXX.md  (the story)
3. Any files listed in the story's "Context" section

Architecture rules from CLAUDE.md that must be followed:
- Three layers: route → service → adapter. Nothing bleeds between layers.
- ALL data queries must filter by tenant_id. No exceptions.
- ANY operation > 2 seconds must be queued to ARQ. Never block a route handler.
- Write Pydantic schemas FIRST, tests SECOND, implementation THIRD.
- Use structlog for all logging. Zero print() statements.
- Heavy imports (Docling, Anthropic SDK) must be lazy: inside function body.

Protocol:
1. Read all the listed files.
2. Show me your implementation plan: which files you will create, which you will modify, and how each acceptance criterion will be satisfied.
3. Do NOT write any code yet.
4. Wait for my approval.
5. After approval: implement in this order — schemas → tests → implementation.
6. After implementation: tell me the command to run to verify it works.
```

### Frontend Story Prompt (for `ravenbase-web/`)

```
I need you to implement STORY-XXX.

Before starting, read these files completely:
1. CLAUDE.md  (frontend rules — mandatory)
2. docs/design/01-design-system.md  (colors, typography, tokens)
3. docs/stories/EPIC-XX-name/STORY-XXX.md  (the story)
4. docs/design/03-screen-flows.md  (if this story has a layout component)

Rules from CLAUDE.md that must be followed:
- NO <form> tags. Use div + onClick handlers.
- ALL styling via Tailwind classes only. No inline styles.
- ALL API calls via apiFetch() from lib/api.ts. Never raw fetch().
- ALL API response data validated with Zod schemas.
- Use shadcn/ui components. Check components/ui/ before building anything new.
- Use TanStack Query (useQuery/useMutation) for all server state.
- TypeScript strict mode. Zero 'any'.
- (marketing)/ routes → light mode. (dashboard)/ routes → dark mode.

Protocol:
1. Read all the listed files.
2. Show me your implementation plan: which components you will create, which routes, and how each acceptance criterion maps to code.
3. Do NOT write any code yet.
4. Wait for my approval.
5. After approval: implement.
6. After implementation: tell me the npm command to verify the build passes.
```

### Parallel Session Prompt (for Window 1 — running both sessions at once)

**Session A (Terminal 1 — backend):**
```
Implement STORY-002: PostgreSQL Schema + Alembic Migrations.
Read: CLAUDE.md, docs/stories/EPIC-01-foundation/STORY-002.md,
docs/architecture/02-database-schema.md.
Show plan first. Do not implement yet.
```

**Session B (Terminal 2 — frontend):**
```
Implement STORY-021: Landing Page.
Read: CLAUDE.md, docs/design/01-design-system.md,
docs/design/03-screen-flows.md, docs/stories/EPIC-07-marketing/STORY-021.md.
This story has zero backend dependencies.
Show plan first. Do not implement yet.
```

---

## Phase 6 — Sprint Execution Order

Work through sprints in sequence. A sprint is complete only when its Definition of Done is
fully checked. There are no time targets — move when the work is done, not when the clock says so.

See `docs/DEVELOPMENT_LOOP.md` for the exact per-story execution loop.
See `docs/PARALLEL_DEV_GUIDE.md` for the full sprint sequence table.

**The only thing you do at the start of every Claude Code session:**
Open the session in the correct repo, then paste the Agent Implementation Brief
from the current story file. Nothing else. The Brief tells the agent what to read.

**How to know which story is next:**
Check `docs/stories/epics.md`. The first row with status 🔲 is your next sprint.
Never skip. Never work on a later story while an earlier one is 🔲.

---

## Phase 7 — After Each Backend Story: Regenerate Client

Every time a backend story adds or changes an API endpoint, run this in the web repo:

```bash
# Make sure API server is running first:
cd ~/ravenbase/ravenbase-api
make dev-up && uv run uvicorn src.api.main:app --reload &

# In web repo:
cd ~/ravenbase/ravenbase-web
npm run generate-client
git add src/lib/api-client/
git commit -m "chore: regenerate API client after STORY-XXX"
```

---

## Quick Reference Card

```
BACKEND SESSION                     FRONTEND SESSION
────────────────────────────        ─────────────────────────────
cd ravenbase-api                  cd ravenbase-web
claude                              claude
Read: CLAUDE.md + story             Read: CLAUDE.md + design/01 + story
make dev-up      (infra up)         npm run dev
make worker      (ARQ up)           npm run generate-client  (after BE story)
make quality     (lint + types)     npm run build  (TypeScript check)
make test        (all tests)        npm run test   (vitest)
make ci-local    (both above)

SHARED CONTRACT: docs/architecture/03-api-contract.md
SHARED DESIGN:   docs/design/01-design-system.md
EPICS BOARD:     docs/stories/epics.md  (update status here)
```

---

## Common Mistakes to Avoid

| Mistake | Consequence | Prevention |
|---|---|---|
| Starting frontend story before backend endpoints exist | Frontend agent invents its own fetch URLs | Strictly follow the execution order in Phase 6 |
| Skipping "Show plan first" | Agent implements wrong thing; hard to undo | Always require plan before code |
| Not running `npm run generate-client` after backend changes | TypeScript errors; frontend using stale API types | Add to your post-backend-story checklist |
| Running both sessions on stories with shared dependencies | Race conditions, conflicting implementations | Only parallelize during the specified windows in PARALLEL_DEV_GUIDE.md |
| Letting agent add new npm/pip packages without review | Dependency bloat, security risks | CLAUDE.md rule: "Always ask before adding a package" |
| Not committing between stories | Messy git history; hard to isolate bugs | One commit per story, every time |
