# STORY-001: API Repo Scaffold + Web Repo Scaffold + Makefile + Docker Compose

**Epic:** EPIC-01 — Foundation Infrastructure
**Priority:** P0
**Complexity:** Medium
**Depends on:** Nothing (first story)
**Type:** Cross-repo
**Repo:** ravenbase-api + ravenbase-web

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — infrastructure scaffolding story (repos, Docker Compose, Makefile).

## Component
Infrastructure

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, read completely)
> 2. `docs/development/00-project-structure.md` — exact directory layout for both repos
> 3. `docs/architecture/01-tech-stack-decisions.md` — ADR-007 (uv), ADR-008 (Railway+Vercel)
> 4. `docs/KICKSTART.md` — exact commands to create both repos (Phase 1 and Phase 2)

---

## User Story
As a developer, I want a complete, working project structure so that every subsequent story has a consistent foundation to build on.

## Context
This is the first story. There is no existing code. The goal is to create both repositories with correct scaffolding so all future agent sessions start from a clean, understood state.

Reference:
- `docs/CLAUDE.md` — architecture rules
- `docs/development/00-project-structure.md` — exact directory structure
- `docs/architecture/01-tech-stack-decisions.md` — ADR-007 (uv), ADR-008 (Railway+Vercel)

## Acceptance Criteria
- [ ] AC-1: `ravenbase-api/` repo exists with full directory structure per `development/00-project-structure.md`
- [ ] AC-2: `ravenbase-web/` repo exists with Next.js 15 App Router + shadcn/ui initialized
- [ ] AC-3: `docker-compose.yml` (base) + `docker-compose.override.yml` (dev) exists in API repo
- [ ] AC-4: `Makefile` has all commands: `dev-up`, `dev-down`, `migrate`, `seed`, `quality`, `test`, `ci-local`, `worker`
- [ ] AC-5: `uv sync --dev` installs all dependencies without errors
- [ ] AC-6: `npm install` in web repo completes without errors
- [ ] AC-7: `docker-compose up postgres redis` starts without errors
- [ ] AC-8: `pyrightconfig.json`, `ruff.toml`, `.pre-commit-config.yaml` exist and are correctly configured
- [ ] AC-9: `.envs/.env.example` contains all required environment variable names with comments
- [ ] AC-10: `src/api/main.py` has a minimal FastAPI app with `/health` endpoint returning `{"status": "ok"}`

## Technical Notes

### Files to Create (API repo)

```
ravenbase-api/
├── CLAUDE.md                    ← copy from docs/CLAUDE.md
├── pyproject.toml               ← with all approved packages
├── uv.lock                      ← committed after uv sync
├── ruff.toml
├── pyrightconfig.json
├── .pre-commit-config.yaml
├── Makefile
├── Dockerfile.api
├── Dockerfile.worker
├── docker-compose.yml
├── docker-compose.override.yml
├── docker-compose.prod.yml
├── .envs/
│   └── .env.example
├── alembic/
│   ├── alembic.ini
│   └── env.py
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI app + lifespan + CORS
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          ← stub require_user (returns mock in dev)
│   │   │   └── db.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── errors.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── base.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── base.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py
│   └── workers/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/                ← COMMITTED to git — required by integration tests
│   │   ├── sample.pdf           ← minimal valid 1-page PDF
│   │   ├── sample.txt           ← plain text for ingestion tests
│   │   └── sample_invalid.bin   ← binary file for rejected-upload tests
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
└── scripts/
    └── seed_dev_data.py         ← placeholder that prints "No seed data yet"
```

### Files to Create (Web repo)

```
ravenbase-web/
├── CLAUDE_FRONTEND.md           ← Frontend-specific agent instructions
├── package.json                 ← Based on template, adapted for Ravenbase
├── tsconfig.json                ← strict mode
├── components.json              ← shadcn/ui new-york config
├── app/
│   ├── globals.css              ← Ravenbase design tokens from design/01-design-system.md
│   ├── layout.tsx               ← Root layout: next/font, metadataBase, html lang="en"
│   ├── sitemap.ts               ← Auto-served at /sitemap.xml (built-in Next.js)
│   ├── robots.ts                ← Auto-served at /robots.txt (built-in Next.js)
│   ├── not-found.tsx            ← Branded 404 page (see SEO spec + error page spec)
│   ├── error.tsx                ← Root error boundary
│   ├── page.tsx                 ← Redirect to /dashboard or /landing
│   └── (admin)/                ← Internal admin panel — requires ADMIN_USER_IDS env var
│       ├── layout.tsx          ← Admin auth check: verify user.id in ADMIN_USER_IDS
│       ├── page.tsx            ← Stats dashboard
│       ├── users/
│       │   ├── page.tsx        ← User list with search
│       │   └── [id]/
│       │       └── page.tsx    ← User detail + credit adjustment
│       └── middleware.ts       ← Redirects non-admin to /dashboard
├── components/
│   └── brand/
│       ├── RavenbaseLogo.tsx    ← SVG mark, size prop (xs/sm/md/lg/xl), color prop
│       ├── RavenbaseLockup.tsx  ← Mark + "RAVENBASE" in DM Sans 800, gap-2
│       └── index.ts             ← export { RavenbaseLogo, RavenbaseLockup }
├── lib/
│   └── utils.ts                 ← cn() helper
└── .env.local.example
```

### globals.css Content

The `app/globals.css` file must contain the exact CSS token system.
Copy the complete content from `docs/design/01-design-system.md` — the `:root` block,
`.dark` block, `@theme inline` block, and `@layer base` block.

The file starts with:
```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark, .dark *));

:root {
  --background: #f5f3ee;
  /* ... full content in design/01-design-system.md → Section 1: CSS Variables */
}
```

**Do not write this from memory.** Read `docs/design/01-design-system.md` Section 1
and copy the complete CSS block verbatim into `app/globals.css`.

### Brand Components (create in STORY-001-WEB)

Read `docs/design/00-brand-identity.md` → Logo & Wordmark section for:
- The complete SVG path data (4 paths)
- The size scale (xs/sm/md/lg/xl)
- The lockup specification (DM Sans ExtraBold 800, tracking-wider, all caps, gap-2)
- Color usage rules

These two components replace every `Brain` icon and `R` placeholder in the entire codebase.

### Architecture Constraints
- pyproject.toml must use `uv` — no `pip install` commands in Makefile
- FastAPI app must use `lifespan` pattern (not deprecated `on_event`)
- CORS must be set to localhost:3000 in dev, specific domain in prod
- `DB session via Depends(get_db)` pattern must be in place from day 1

### Key Config File Templates

#### pyproject.toml (complete — copy into ravenbase-api/)

```toml
[project]
name = "ravenbase-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlmodel>=0.0.22",
    "alembic>=1.14.0",
    "arq>=0.26.0",
    "redis>=5.2.0",
    "qdrant-client>=1.12.0",
    "neo4j>=5.28.0",
    "docling>=2.14.0",
    "openai>=1.55.0",
    "anthropic>=0.40.0",
    "svix>=1.40.0",
    "python-magic>=0.4.27",
    "supabase>=2.10.0",
    "httpx>=0.27.0",
    "PyJWT>=2.9.0",
    "cryptography>=43.0.0",
    "stripe>=10.0.0",
    "structlog>=24.4.0",
    "sentry-sdk[fastapi]>=2.19.0",
    "pydantic-settings>=2.6.0",
    "presidio-analyzer>=2.2.355",
    "presidio-anonymizer>=2.2.355",
    "sse-starlette>=2.1.0",
    "aiofiles>=24.1.0",
]

[dependency-groups]
dev = [
    "ruff>=0.8.0",
    "pyright>=1.1.391",
    "pre-commit>=4.0.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "pytest-xdist>=3.6.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "C4", "PLC", "ARG"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ARG"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
include = ["src"]
exclude = ["tests"]
```

#### Makefile (complete — copy into ravenbase-api/)

```makefile
.PHONY: dev-up dev-down migrate db-upgrade seed lint-fix format quality test ci-local worker

dev-up:
	docker-compose up -d postgres redis

dev-down:
	docker-compose down

migrate:
	uv run alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed_dev_data.py

lint-fix:
	uv run ruff check src/ tests/ --fix

format:
	uv run ruff format src/ tests/

quality:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
	uv run pyright src/

test:
	docker-compose up -d postgres redis
	uv run pytest tests/ -n auto --cov=src --cov-report=term-missing -q

ci-local: quality test
	@echo "CI passed locally"

worker:
	uv run arq src.workers.main.WorkerSettings --watch src/
```

#### package.json scripts (add to ravenbase-web/package.json)

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "test": "vitest",
  "generate-client": "openapi-ts --input http://localhost:8000/openapi.json --output src/lib/api-client --client axios"
}
```

### Error Pages (create during web scaffold — STORY-001-WEB)

Three special Next.js files that render automatically on navigation errors.
These must be created during scaffolding — adding them later requires a separate deploy.

**`app/not-found.tsx`** — rendered when `notFound()` is called or a URL doesn't exist:
```tsx
// app/not-found.tsx
import Link from "next/link"
import { RavenbaseLockup } from "@/components/brand"

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
      <RavenbaseLockup size="md" />
      <div className="mt-12 text-center max-w-sm">
        <p className="font-mono text-xs text-muted-foreground tracking-wider mb-4">
          ◆ ERROR_404
        </p>
        <h1 className="font-serif text-4xl mb-4">Page not found</h1>
        <p className="text-muted-foreground mb-8">
          This memory doesn't exist in your knowledge graph.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground
                     rounded-full font-medium text-sm hover:bg-primary/90 transition-colors"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  )
}
```

**`app/error.tsx`** — root error boundary for unexpected runtime errors:
```tsx
"use client"  // Error boundaries MUST be Client Components
import { useEffect } from "react"
import { RavenbaseLockup } from "@/components/brand"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log to Sentry in production
    console.error(error)
  }, [error])

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
      <RavenbaseLockup size="md" />
      <div className="mt-12 text-center max-w-sm">
        <p className="font-mono text-xs text-muted-foreground tracking-wider mb-4">
          ◆ SYSTEM_ERROR
        </p>
        <h2 className="font-serif text-4xl mb-4">Something went wrong</h2>
        <p className="text-muted-foreground mb-8">
          An unexpected error occurred. Your memory graph data is safe.
        </p>
        <button
          onClick={reset}
          className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground
                     rounded-full font-medium text-sm hover:bg-primary/90 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
```

**`app/(dashboard)/error.tsx`** — error boundary scoped to dashboard routes:
```tsx
"use client"
import { useEffect } from "react"
import { Button } from "@/components/ui/button"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => { console.error(error) }, [error])

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <p className="font-mono text-xs text-muted-foreground tracking-wider mb-4">
        ◆ PAGE_ERROR
      </p>
      <h2 className="font-serif text-2xl mb-2">This page failed to load</h2>
      <p className="text-muted-foreground text-sm mb-6 max-w-xs">
        Your data is safe. This was likely a temporary glitch.
      </p>
      <Button onClick={reset}>Reload page</Button>
    </div>
  )
}
```

### Creating Test Fixtures

The `tests/fixtures/` directory must be committed with real (minimal) binary files.
Create them as part of STORY-001 scaffolding:

```bash
# Create a minimal valid PDF (raw PDF bytes — parseable but trivial)
python3 -c "
data = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
data += b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
data += b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\n'
data += b'xref\n0 4\n0000000000 65535 f\n'
data += b'trailer<</Root 1 0 R/Size 4>>\n%%%%EOF'
open('tests/fixtures/sample.pdf', 'wb').write(data)
"

# Plain text fixture
echo "Ravenbase test document. Python, TypeScript, machine learning, 2024." \
  > tests/fixtures/sample.txt

# Invalid binary (magic bytes of an EXE — should be rejected by upload endpoint)
python3 -c "open('tests/fixtures/sample_invalid.bin', 'wb').write(b'MZ\x90\x00')"
```

These files are tiny (< 1 KB). Never add them to `.gitignore`.
The agent that creates STORY-001 MUST commit them.

## Definition of Done
- [ ] All ACs verified manually
- [ ] `make quality` passes (0 errors)
- [ ] `curl localhost:8000/health` returns `{"status": "ok"}` after `make dev-up`
- [ ] `npm run build` succeeds in web repo (no TypeScript errors)
- [ ] `components/brand/RavenbaseLogo.tsx` renders the SVG at all 5 size variants
- [ ] `components/brand/RavenbaseLockup.tsx` renders mark + "RAVENBASE" with 8px gap
- [ ] `app/layout.tsx` uses `next/font` for all 3 typefaces (DM Sans, Playfair Display, JetBrains Mono)
- [ ] `app/layout.tsx` exports `metadata` with `metadataBase` set to `https://ravenbase.app`
- [ ] `app/sitemap.ts` and `app/robots.ts` exist
- [ ] `app/not-found.tsx` renders branded 404 (Ravenbase logo, message, link back to dashboard or home)
- [ ] `app/error.tsx` renders branded error boundary with retry button

## Testing This Story

```bash
# Backend quality gate:
make quality
# Expected: 0 ruff errors, 0 pyright errors

# Health check:
make dev-up
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# Frontend build:
cd ravenbase-web && npm run build
# Expected: 0 TypeScript errors, build succeeds
```

**Passing result:** Both repos scaffold correctly. `make quality` and `npm run build` pass from a clean checkout.

---

## Agent Implementation Brief

```
Implement STORY-001: API and Web repo scaffolding.

This is the foundation story — no existing code to build on.

Read first:
1. CLAUDE.md (architecture rules — this defines what you are building)
2. docs/development/00-project-structure.md (exact file list for both repos)
3. docs/architecture/01-tech-stack-decisions.md (ADR-007: uv, ADR-008: Railway+Vercel)
4. docs/KICKSTART.md (setup commands)
5. docs/stories/EPIC-01-foundation/STORY-001.md (this file)

Key constraints:
- pyproject.toml uses uv — no pip commands in Makefile
- FastAPI app uses lifespan pattern (not deprecated on_event)
- CORS: localhost:3000 in dev, ravenbase.app in prod
- uv.lock MUST be committed (not in .gitignore)
- DB sessions via Depends(get_db) from day 1

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test       # backend
npm run build && npm run test   # frontend (if applicable)

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-001 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-001"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-001
git add docs/stories/epics.md && git commit -m "docs: mark STORY-001 complete"
```
