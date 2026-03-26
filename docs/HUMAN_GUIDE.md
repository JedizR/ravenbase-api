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
brew install ngrok/ngrok/ngrok   # For Clerk webhook testing (STORY-018)
# Authenticate ngrok (free account at ngrok.com):
ngrok config add-authtoken YOUR_NGROK_TOKEN
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

# Each repo gets its own CLAUDE.md (different rules for backend vs frontend)
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

# Push to GitHub (use SSH)
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

---

#### Service 1 — Supabase (PostgreSQL + Storage)

1. Go to `supabase.com` → sign in → click **"New project"**
2. Fill in:
   - **Name:** `ravenbase`
   - **Database Password:** generate a strong one → **copy it immediately** into your password manager
   - **Region:** pick closest to you
   - Click **"Create new project"** — takes ~2 minutes

3. **Get your Project URL and API keys:**
   - Left sidebar → **Settings** → **API**
   - Copy and save all three:
     - **Project URL** → `https://abcdefghijklmno.supabase.co`
     - **anon** key → the long `eyJ...` string (for frontend/client use)
     - **service_role** key → click **"Reveal"** → copy it (for backend/server use)

   > **Note on Supabase's new key format:** Supabase is transitioning to `sb_publishable_...` and `sb_secret_...` keys. If your project shows these instead of `anon` / `service_role`, use `sb_publishable_...` where the guide says anon key, and `sb_secret_...` where it says service_role key. Both formats work during the transition period.

4. **Get your Database URL:**
   - Left sidebar → **Settings** → **Database**
   - Under **"Connection string"** → select the **"URI"** tab
   - Copy the URI: `postgresql://postgres:[YOUR-PASSWORD]@db.REF.supabase.co:5432/postgres`
   - Replace `[YOUR-PASSWORD]` with your DB password from step 2
   - Change the scheme to `postgresql+asyncpg://` for SQLAlchemy async

5. **Create the Storage bucket:**
   - Left sidebar → **Storage** → **"New bucket"**
   - Name: `ravenbase-sources`
   - Toggle **"Public bucket"** to **OFF** (keep it private)
   - Click **"Save"**

> **RLS note:** Do not enable RLS manually now. The agent running STORY-002 creates all tables via Alembic migrations. RLS policies are configured by the agent in the relevant stories.

---

#### Service 2 — Clerk (Auth)

1. Go to `clerk.com` → **"Create application"**
2. Fill in:
   - **Application name:** `Ravenbase`
   - Enable: **Email** and **Google** sign-in (toggle both on)
   - Click **"Create application"**

3. **Your API keys are shown immediately on the overview page:**
   - **Publishable Key** → `pk_test_...` — visible directly on the page
   - **Secret Key** → click the eye icon to reveal → `sk_test_...` → copy it

4. **Webhook** — set this up later during STORY-018 when you have a running server. Skip for now.

5. **Your Clerk User ID** — you don't have one yet. It's created when you register as the first user in your own app during STORY-018 testing. Come back then:
   - Left sidebar → **Users** → click your account → copy **User ID** (`user_2abc...`)
   - Set this as `ADMIN_USER_IDS` in both env files

---

#### Service 3 — Qdrant Cloud (Vector Store)

1. Go to `cloud.qdrant.io` → sign up with email, Google, or GitHub

2. You'll see a **"Create a Free Cluster"** section. Fill in:
   - **Cluster name:** `ravenbase` (just a label)
   - **Cloud provider + Region:** pick any — choose the region closest to you
   - Click **"Create Free Cluster"**

3. **⚠️ A dialog appears with your API key — copy it immediately.** It is shown only once. If you miss it, you can only generate a new one, not retrieve the original. Save it to your password manager now.

4. Click **"Continue"** → you land on the cluster detail page

5. **Get your Cluster URL:**
   - On the cluster detail page, find the **"Endpoint"** section
   - The URL looks like: `https://xyz-example.eu-central.aws.cloud.qdrant.io`
   - Copy this — this is your `QDRANT_URL`

6. **If you missed the API key**, generate a new one:
   - Cluster detail page → **"API Keys"** tab → **"Create"**
   - Name: `ravenbase-dev`, leave expiration blank → click **"Create"** → copy immediately

7. **Verify the connection works:**
   ```bash
   curl https://YOUR-CLUSTER.cloud.qdrant.io:6333 \
     --header 'api-key: YOUR_API_KEY'
   # Expected: {"title":"qdrant - vector search engine","version":"..."}
   ```

> **Free tier:** 1 node, 1GB storage, ~1M vectors at 768 dimensions. Sufficient for the entire MVP. Clusters suspend after 1 week of inactivity and are deleted after 4 weeks — log in occasionally during development.

---

#### Service 4 — Neo4j AuraDB (Graph Database)

1. Go to `neo4j.com/cloud/platform/aura-graph-database` → click **"Start Free"**
2. Sign up or log in → you land in the **Aura Console**
3. Click **"New Instance"** → select **"AuraDB Free"**
4. Fill in:
   - **Instance name:** `ravenbase`
   - **Region:** pick closest to you
   - Leave other settings as default
   - Click **"Create"**

5. **⚠️ A dialog appears — do ALL of these right now:**
   - Click **"Download and Continue"** → saves a `.txt` credentials file to your machine
   - The file contains your **Connection URI**, **Username**, and **Password**
   - **The password is shown only once and cannot be recovered.** If you lose it, you must destroy the instance and create a new one.

6. **Open the downloaded credentials file** and save to your password manager:
   - `NEO4J_URI` → `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - `NEO4J_USERNAME` → `neo4j`
   - `NEO4J_PASSWORD` → the long generated password

7. Wait ~2 minutes for the instance status to show **"Running"**

> **Free tier limits:** 200k nodes, 400k relationships. More than sufficient for MVP and beta. Instances inactive for 30 days are paused with a warning email before deletion.

---

#### Service 5 — OpenAI (Embeddings)

1. Go to `platform.openai.com/api-keys` → sign in → click **"Create new secret key"**
2. Name: `ravenbase-dev` → click **"Create secret key"**
3. **Copy the key immediately** (`sk-...`) — shown only once → save to password manager
4. **Set a spending limit:** Left sidebar → **Settings** → **Limits** → set **"Monthly budget"** to `$20`

---

#### Service 6 — Anthropic (User-facing LLM)

1. Go to `console.anthropic.com` → sign in → **API Keys** (left sidebar)
2. Click **"Create Key"** → Name: `ravenbase-dev` → click **"Create Key"**
3. **Copy the key** (`sk-ant-...`) → save to password manager

---

#### Service 7 — Google AI Studio (Background LLM — Gemini Flash)

1. Go to `aistudio.google.com/apikey`
2. Click **"Create API key"** → select or create a Google Cloud project → click **"Create API key in existing project"**
3. **Copy the key** (`AIza...`) → save to password manager

> Optional for local dev — background tasks fall back to Claude Haiku if absent (~3× cost). Set it now to save money from sprint 1.

---

#### Service 8 — Stripe (Payments) + Resend (Email)

**Stripe:**

1. Go to `stripe.com` → sign in → **Developers** → **API keys**
2. Make sure you're in **Test mode** (toggle in top-right of Stripe dashboard)
3. Save to password manager:
   - **Publishable key** → `pk_test_...` (click to copy)
   - **Secret key** → click **"Reveal test key"** → `sk_test_...` → copy

4. The **Stripe Webhook Secret** (`whsec_test_...`) is generated by `stripe listen` during STORY-022 — leave it as a placeholder for now.

**Resend:**

1. Go to `resend.com` → sign up → left sidebar → **API Keys** → **"Create API Key"**
2. Name: `ravenbase-dev`, Permission: **Full access**
3. Click **"Add"** → **copy the key immediately** (`re_...`) → save to password manager

4. **Resend Webhook** (for bounce/complaint handling — needed for STORY-032):
   - Left sidebar → **Webhooks** → **"Add Webhook"**
   - You'll fill in the URL during STORY-032. The **Signing Secret** (`whsec_...`) appears on the webhook detail page after creation → save it.

> Resend free tier: 3,000 emails/month, 100/day. Leave `RESEND_API_KEY` blank in `.env.dev` to skip sending real emails locally — the backend logs a warning and skips gracefully.

---

### 2.4 Create Environment Files `[HUMAN]`

Create this file: **`ravenbase-api/.envs/.env.dev`**

```bash
mkdir -p ~/ravenbase/ravenbase-api/.envs
cat > ~/ravenbase/ravenbase-api/.envs/.env.dev << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_DB_PASS@db.YOUR_REF.supabase.co:5432/postgres
REDIS_URL=redis://localhost:6379

# Auth
CLERK_SECRET_KEY=sk_test_YOUR_KEY
CLERK_WEBHOOK_SECRET=whsec_placeholder   # Fill in during STORY-018 using ngrok

# AI
OPENAI_API_KEY=sk-YOUR_KEY
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY
GEMINI_API_KEY=AIza...                   # Optional for local dev

# Vector + Graph
QDRANT_URL=https://xyz-example.eu-central.aws.cloud.qdrant.io
QDRANT_API_KEY=YOUR_QDRANT_KEY
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD

# Storage
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ_YOUR_SERVICE_ROLE_KEY
STORAGE_BUCKET=ravenbase-sources

# Payments + Email
STRIPE_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_WEBHOOK_SECRET=whsec_placeholder  # Fill in during STORY-022: stripe listen
RESEND_API_KEY=                          # Leave blank to skip emails in local dev
RESEND_WEBHOOK_SECRET=whsec_placeholder  # Fill in during STORY-032

# Security
CLOUDFLARE_ORIGIN_SECRET=changeme        # Only needed in production

# Config
APP_ENV=development
ENABLE_PII_MASKING=false
CONFLICT_SIMILARITY_THRESHOLD=0.87
MAX_DAILY_LLM_SPEND_USD=50.0
ADMIN_USER_IDS=user_placeholder          # Fill in after STORY-018
EOF
```

Create this file: **`ravenbase-web/.env.local`**

```bash
cat > ~/ravenbase/ravenbase-web/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY
CLERK_SECRET_KEY=sk_test_YOUR_KEY
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ_YOUR_ANON_KEY
ADMIN_USER_IDS=user_placeholder          # Fill in after STORY-018 — same as backend
# NEXT_PUBLIC_POSTHOG_KEY=phc_YOUR_KEY   # Optional — cookie banner only shows if set
EOF
```

### 2.5 Install Skills into Claude Code `[HUMAN]`

Run once globally. Applies to all Claude Code sessions.

```bash
# In terminal:
npx skills add shadcn-ui/ui --skill shadcn -a claude-code -g
npx skills add secondsky/claude-skills --skill tailwind-v4-shadcn -a claude-code -g
npx skills add Jeffallan/claude-skills --skill fastapi-expert -a claude-code -g

# Inside any active Claude Code session:
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
/install-skill https://github.com/aj-geddes/claude-code-bmad-skills
```

| Skill | Does | Activates when |
|---|---|---|
| `shadcn` | Reads your live `components.json` at session start | Any shadcn/ui work |
| `tailwind-v4-shadcn` | Tailwind v4 gotchas, `@theme inline` pattern | Any Tailwind v4 work |
| `fastapi-expert` | Async patterns, lifespan, dependency injection | Any FastAPI work |
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

### Step 1 — Paste the Brief `[HUMAN]`

Find the **Agent Implementation Brief** at the bottom of the story file. Copy it. Paste it as your first message.

**For cross-repo stories** (STORY-007, STORY-008, STORY-018, STORY-028, STORY-036): backend session first → Frontend Agent Brief in a second session after backend is merged.

### Step 2 — Agent Reads `[AGENT]`

Reads: `CLAUDE.md` → `project-status.md` → last 2–3 `journal.md` entries → story file → all "Before You Start" files.

### Step 3 — Agent Plans `[AGENT]`

Outputs files to create, files to modify, how each AC maps to code.
**Stops and waits for your explicit approval.**

### Step 4 — You Approve `[HUMAN]`

If correct: `"Approved. Proceed."`
If wrong, redirect before any code is written.

### Step 5 — Agent Implements `[AGENT]`

Strict order: **schemas/models → tests → implementation**

### Step 6 — Agent Runs Quality Gate `[AGENT]`

```
Backend:   make quality → 0 ruff + pyright errors
           make test    → 0 failures, coverage ≥ 70%
Frontend:  npm run build → 0 TypeScript errors, 0 warnings
           npm run test  → 0 failures
```

Agent fixes and re-runs if gate fails. Does not commit until clean.

### Step 7 — Agent Verifies `[AGENT]`

Runs every command from "Testing This Story". Confirms every AC checkbox is met.

### Step 8 — Agent Commits `[AGENT]`

```bash
git add -A
git commit -m "feat(ravenbase): STORY-XXX brief description"
git push
```

### Step 9 — Agent Regenerates Client (if needed) `[AGENT]`

Only when the story added or changed an API endpoint:

```bash
cd ../ravenbase-web
npm run generate-client
git add src/lib/api-client/
git commit -m "chore: regenerate client after STORY-XXX"
git push && cd ../ravenbase-api
```

Stories that always require it:
`005, 007-BE, 008-BE, 010, 013, 016, 018-BE, 023, 024, 026, 028-BE, 029, 034, 035, 036-BE`

### Step 10 — Agent Updates All State `[AGENT]`

```bash
# epics.md: 🔲 → ✅
# project-status.md: sprint, next story, last completed
# story-counter.txt: increment by 1
# journal.md: append entry with all 6 fields + update stats table

git add docs/stories/epics.md docs/.bmad/project-status.md docs/.bmad/journal.md
git commit -m "docs: mark STORY-XXX complete"
git push
```

### Step 11 — You Verify on GitHub `[HUMAN]`

Confirm commit landed. CI is green. Pick next 🔲. Return to Loop Start.

---

## Part 4 — The Three Situations

### Situation A — Session dies between stories

```bash
cd ~/ravenbase/ravenbase-api  # or ravenbase-web
claude
# Paste the Agent Implementation Brief from the next story file
```

No special handling needed.

### Situation B — Session dies mid-story

```bash
git log --oneline -5 && git status   # What exists
# Edit epics.md → 🔲 to 🔄
# Edit project-status.md → add session note
git add docs/stories/epics.md docs/.bmad/project-status.md
git commit -m "docs: STORY-XXX in progress — resume notes added" && git push
```

Paste this resume message in Claude Code:
```
I am resuming STORY-XXX: [title]. It is partially complete.

Read: CLAUDE.md, project-status.md, last 2–3 journal.md entries,
the story file (note [x] ACs), and [list files created so far].

Tell me: which ACs are done, which remain, and your plan for ONLY
the remaining work. Do not re-implement. Show plan first.
```

### Situation C — Restart from scratch

```bash
# Delete story files, edit epics.md → 🔲, commit, start fresh session
```

---

## Part 5 — The Backend Gate

After Sprint 17, before any frontend story:

```bash
rm -rf .venv && uv sync --dev
make test && make quality          # Must both be clean
cd ../ravenbase-web && npm ci
npm run generate-client            # Must produce non-empty src/lib/api-client/
```

```
[ ] All 17 backend stories merged to main
[ ] make test: 0 failures from clean checkout
[ ] make quality: 0 errors
[ ] npm run generate-client: non-empty typed client
[ ] curl localhost:8000/health → all 4 services healthy
```

---

## Part 6 — Sprint Sequence

### Phase A — Backend (Sprints 1–17, `ravenbase-api`)

| Sprint | Story | Done when |
|---|---|---|
| 1 | STORY-001 | `/health` → `{"status":"ok"}` |
| 2 | STORY-002 | Migrations clean. All tables exist |
| 3 | STORY-003 + STORY-004 | Health: qdrant+neo4j ok. ARQ starts |
| 4 | STORY-005 | Upload → 202. File in Supabase Storage |
| 5 | STORY-006 | PDF parsed + embedded. Searchable in Qdrant |
| 6 | STORY-007-BE | SSE stream emits progress to curl |
| 7 | STORY-008-BE | `/v1/ingest/text` accepts + queues |
| 8 | STORY-009 + STORY-010 | Neo4j nodes populated. Graph API works |
| 9 | STORY-012 + STORY-013 | Conflict detected. Resolve + undo work |
| 10 | STORY-015 + STORY-016 | Retrieval returns chunks. MetaDoc streams SSE |
| 11 | STORY-018-BE | JWT validated. Clerk webhook creates User |
| 12 | STORY-023 | Credits deducted. 402 on insufficient balance |
| 13 | STORY-024 | Full cascade deletion across 4 stores |
| 14 | STORY-025 | PII masking active. Tests pass |
| 15 | STORY-026 | Chat streams tokens. Credits deducted |
| 16 | STORY-028-BE | Import prompt endpoint works |
| 17 | STORY-029 | Graph query → cypher + nodes. Write ops rejected |

**→ BACKEND GATE ← (see Part 5)**

### Phase B — Frontend (Sprints 18–35, `ravenbase-web`)

| Sprint | Story | Done when |
|---|---|---|
| 18 | STORY-001-WEB | `npm run build` passes. `--primary: #2d4a3e` in globals.css |
| 19 | STORY-018-FE | Register → login → `/dashboard` |
| 20 | STORY-019 + STORY-020 | Onboarding wizard. Profile switching |
| 21 | STORY-007-FE + STORY-008-FE | IngestionProgress streams. Omnibar works |
| 22 | STORY-011 | Graph Explorer renders |
| 23 | STORY-014 | Memory Inbox: all 3 flows |
| 24 | STORY-017 | Workstation streams. Export works |
| 25 | STORY-021 + STORY-022 | Landing page live. Stripe checkout works |
| 26 | STORY-027 | Chat UI streams with citations |
| 27 | STORY-028-FE | Import helper UI works |
| 28 | STORY-030 | Graph query bar highlights nodes |
| 29 | STORY-031 | Dark mode toggle persists |
| 30 | STORY-032 | Welcome + low-credits emails send |
| 31 | STORY-033 | Privacy + Terms pages. Cookie banner |
| 32 | STORY-034 | Referral codes working |
| 33 | STORY-035 | Export ZIP + email link |
| 34 | STORY-036 | Admin dashboard works |
| 35 | STORY-037 | CRON purge at day 180 |

---

## Part 7 — Story-Specific Concerns

### STORY-001 `[HUMAN: check before approving]`
- `pyproject.toml` uses `uv` syntax (not Poetry)
- FastAPI uses `lifespan` context manager (not `@app.on_event`)
- `aiosqlite` is in `[dependency-groups.dev]`

### STORY-001-WEB `[HUMAN: verify after completion]`
`app/globals.css` must contain `--primary: ...` resolving to `#2d4a3e` and `--background: ...` resolving to `#f5f3ee`. Wrong tokens = every frontend story builds with wrong colors.

### STORY-006 `[HUMAN: budget a full session]`
Content moderation (AC-11) must run **before** Docling. Docling backend: `pypdfium2` with `generate_page_images=False`.

### STORY-009 `[HUMAN: verify LLMRouter]`
Agent must implement `src/adapters/llm_router.py` using LiteLLM SDK. Routes to `gemini/gemini-2.5-flash` primary, Claude Haiku fallback.

### STORY-018-BE `[HUMAN: critical test]`
```bash
curl localhost:8000/v1/graph/nodes
# Must return 401
```
If not 401, stop everything and fix. Every story after depends on this.

**Local webhook testing:**
```bash
ngrok http 8000
# URL: https://abc123.ngrok-free.app
# Clerk Dashboard → Configure → Webhooks → Add Endpoint:
#   URL: https://abc123.ngrok-free.app/webhooks/clerk
#   Events: user.created, user.deleted
#   Signing Secret → CLERK_WEBHOOK_SECRET in .envs/.env.dev

# After testing, register yourself at localhost:3000/register
# Clerk Dashboard → Users → your account → copy User ID (user_2abc...)
# Set ADMIN_USER_IDS=user_2abc... in BOTH .envs/.env.dev AND .env.local
```

### STORY-022 `[HUMAN: start Stripe CLI first]`
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
# Printed secret → STRIPE_WEBHOOK_SECRET in .envs/.env.dev
# This is DIFFERENT from the Stripe dashboard webhook secret
```

### STORY-032 `[HUMAN: Resend webhook]`
```bash
ngrok http 8000
# Resend Dashboard → Webhooks → Add Webhook
#   URL: https://YOUR_NGROK_URL/webhooks/resend
#   Events: email.bounced, email.complained
#   Signing Secret → RESEND_WEBHOOK_SECRET in .envs/.env.dev
```

### STORY-036 `[HUMAN: both env files]`
`ADMIN_USER_IDS` must be in **both** `.envs/.env.dev` and `.env.local`. Next.js server components read it independently.

### STORY-037 `[HUMAN: two constraints]`
1. `ActivityTrackingMiddleware` must use `asyncio.create_task()` — never `await`
2. Purge must check BOTH `User.tier IN ('pro', 'team')` AND `settings.admin_user_ids`

---

## Part 8 — Context Window Management

At ~80% context: push to complete and commit the current story rather than starting a new one. Fresh agents work fine — every story brief is self-contained.

---

## Part 9 — Production Deployment Checklist

### Railway (Backend)
```
[ ] GEMINI_API_KEY set (Haiku fallback costs 3× more)
[ ] MAX_DAILY_LLM_SPEND_USD=200.0
[ ] CLOUDFLARE_ORIGIN_SECRET set (32-char hex)
[ ] ADMIN_USER_IDS set (production Clerk user ID)
[ ] RESEND_WEBHOOK_SECRET set
[ ] STRIPE_WEBHOOK_SECRET = production webhook (not test mode)
[ ] APP_ENV=production
[ ] ENABLE_PII_MASKING=true
```

### Vercel (Frontend)
```
[ ] ADMIN_USER_IDS set (same as Railway)
[ ] NEXT_PUBLIC_API_URL → production Railway URL
[ ] NEXT_PUBLIC_POSTHOG_KEY set if you want analytics
```

### Cloudflare
```
[ ] WAF + Bot Fight Mode enabled
[ ] Origin secret header rule active
[ ] Rate limiting: 100 req / 10s / IP
```

### Monitoring
```
[ ] Better Uptime: /health every 60s
[ ] Alert: llm_circuit_breaker.TRIPPED (page immediately)
[ ] Alert: Dead Letter Queue > 0
[ ] Supabase PITR enabled
```

### Multi-Database Restore Order
PostgreSQL first → Qdrant (`make reindex-missing`) → Neo4j (`make regraph-missing`). Never restore Qdrant or Neo4j before PostgreSQL.

---

## Part 10 — Files You Interact With Every Day

| File | Purpose | Who updates |
|---|---|---|
| `docs/stories/epics.md` | Story status board | Agent after each story |
| `docs/.bmad/project-status.md` | Current sprint, next story | Agent after each story |
| `docs/.bmad/journal.md` | Append-only history | Agent after each story |
| `docs/.bmad/story-counter.txt` | Story number counter | Agent after each story |
| `docs/.bmad/resume-protocol.md` | How to resume mid-story | You read when needed |
| Story files (`STORY-XXX.md`) | Agent Brief you paste | You read; agent checks ACs |
| `CLAUDE.md` (repo root) | Backend rules | Reference when redirecting |
| `CLAUDE.md` (`ravenbase-web`) | Frontend rules | Reference when redirecting |

---

## Part 11 — Moving to a Different Machine

```bash
git clone git@github.com:YOUR_USERNAME/ravenbase-api.git
git clone git@github.com:YOUR_USERNAME/ravenbase-web.git
# Re-create env files from password manager
# Re-install: uv, gh, stripe CLI, ngrok, Node 20+, Docker
# Re-install Claude Code skills (Part 2, Section 2.5)
cat ravenbase-api/docs/.bmad/project-status.md  # Resume from here
```

---

## Part 12 — The One-Line Summary

> Read `project-status.md` → open Claude Code → paste the Agent Brief → approve the plan → watch the agent build → confirm the commit on GitHub.

Everything else is automated.

---

## Audit Status ✅

**Verified against `docs_newest_version.zip` — 81 files, 37 stories, 35 sprints.**
**Zero failures across all 20 structural check categories.**