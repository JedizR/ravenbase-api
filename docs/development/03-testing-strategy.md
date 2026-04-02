# Development — 03. Testing Strategy

> **Cross-references:** `development/02-coding-standards.md` | `docs/CLAUDE.md`
>
> **Source:** Adapted from PROD_LV_DEV_FOR_SOLO_DEV_v4.md Part 12 — Ravenbase specific

---

## Test Pyramid

```
         / \
        /E2E\       ← Playwright: happy path per user story
       /─────\
      / Integ \     ← pytest: real DB + Redis, mocked LLMs
     /─────────\
    /   Unit    \   ← pytest: complex business logic only
   /─────────────\
```

**Coverage target:** ≥70% combined (integration + unit).

**Rule:** Do NOT write unit tests for simple CRUD operations. Write integration tests that test the full request→DB→response cycle. Unit tests are only for complex business logic (conflict scoring, re-ranking, credit calculations).

---

## Backend Test Setup (pytest)

```python
# tests/conftest.py — CORRECT async pattern
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from src.api.main import app

# NOTE: requires `aiosqlite` in dev dependencies
# Add with: uv add --dev aiosqlite
@pytest_asyncio.fixture(scope="session")
async def engine():
    """Async in-memory SQLite for fast unit/integration tests.

    For critical migration-accuracy tests, swap this URL for the real
    PostgreSQL test database and run Alembic migrations instead of
    metadata.create_all().
    """
    async_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield async_engine
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()
```

> **Important:** `aiosqlite` must be in dev dependencies. The agent creating STORY-001's
> `pyproject.toml` must include `aiosqlite>=0.20.0` in `[dependency-groups.dev]`.

# ─── Auth Fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user():
    return {"user_id": "test-user-uuid-0001", "email": "test@example.com"}

@pytest.fixture
async def authenticated_client(mock_user):
    """HTTP client with mocked Clerk auth."""
    with patch("src.api.dependencies.auth.require_user", return_value=mock_user):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

# ─── External Service Fixtures ────────────────────────────────────────────────

@pytest.fixture
def mock_qdrant():
    """Mock Qdrant adapter for unit tests."""
    with patch("src.adapters.qdrant_adapter.QdrantAdapter") as mock:
        mock.return_value.search = AsyncMock(return_value=[])
        mock.return_value.upsert = AsyncMock(return_value=True)
        mock.return_value.delete_by_filter = AsyncMock(return_value=0)
        yield mock

@pytest.fixture
def mock_anthropic():
    """Mock Anthropic adapter for unit tests."""
    with patch("src.adapters.anthropic_adapter.AnthropicAdapter") as mock:
        mock.return_value.classify_conflict = AsyncMock(return_value={
            "classification": "CONTRADICTION",
            "confidence": 0.94,
            "reasoning": "Test reasoning",
        })
        yield mock

@pytest.fixture
def mock_arq_pool():
    """Mock ARQ pool for tests that call endpoints which enqueue jobs.

    Usage: include this fixture in any test that hits an endpoint that calls
    request.app.state.arq_pool.enqueue_job(...)

    Example:
        async def test_upload_enqueues_job(authenticated_client, mock_arq_pool):
            response = await authenticated_client.post("/v1/ingest/upload", ...)
            assert response.status_code == 202
            mock_arq_pool.enqueue_job.assert_called_once()
    """
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=AsyncMock(job_id="test-job-id-001"))
    with patch.object(app.state, "arq_pool", mock_pool, create=True):
        yield mock_pool

# ─── Sample Data Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<</Type /Catalog>>\nendobj\n"

@pytest.fixture
def sample_chunks() -> list[dict]:
    return [
        {"content": "I use TypeScript for all projects", "page_number": 1, "chunk_index": 0},
        {"content": "React is my primary frontend framework", "page_number": 1, "chunk_index": 1},
        {"content": "I worked at Sense Info Tech in 2024", "page_number": 2, "chunk_index": 2},
    ]
```

```toml
# pyproject.toml — pytest config
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Critical Integration Tests (Must Pass Before Each Sprint Merge)

```python
# tests/integration/api/test_ingest_endpoints.py

async def test_upload_returns_job_id(authenticated_client, mock_qdrant):
    """End-to-end: upload file → receive job_id → job exists in Redis."""
    with open("tests/fixtures/sample.pdf", "rb") as f:
        response = await authenticated_client.post(
            "/v1/ingest/upload",
            files={"file": ("sample.pdf", f, "application/pdf")},
        )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"

async def test_duplicate_file_rejected(authenticated_client, db_session):
    """Same SHA-256 hash for same user returns existing source_id."""
    # Upload twice
    for _ in range(2):
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = await authenticated_client.post(...)
    
    # Second upload returns duplicate=true
    assert response.json()["duplicate"] is True

async def test_invalid_file_type_returns_422(authenticated_client):
    response = await authenticated_client.post(
        "/v1/ingest/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_FILE_TYPE"

# tests/integration/test_tenant_isolation.py

async def test_qdrant_tenant_isolation(mock_qdrant):
    """CRITICAL: User A's search must never return User B's chunks."""
    user_a = "user-a-uuid"
    user_b = "user-b-uuid"

    # Seed identical text for both users
    await qdrant.upsert(user_a, "source-a", [{"content": "test content", "chunk_index": 0}])
    await qdrant.upsert(user_b, "source-b", [{"content": "test content", "chunk_index": 0}])

    # User A searches — must get only their chunks
    results = await qdrant.search(query_vector=[0.1] * 1536, tenant_id=user_a)
    for r in results:
        assert r.payload["tenant_id"] == user_a, "TENANT ISOLATION VIOLATION"

async def test_gdpr_deletion_cascade(authenticated_client, db_session):
    """After delete, zero data in all stores."""
    # 1. Upload and process a file
    # 2. Verify in all stores (PG, Qdrant, Neo4j)
    # 3. DELETE /v1/account
    # 4. Wait for cascade job
    # 5. Assert all stores empty for tenant

    response = await authenticated_client.delete("/v1/account")
    assert response.status_code == 202

    # Wait for cascade
    import asyncio
    await asyncio.sleep(65)  # SLA: 60s

    # Assert empty
    sources_count = await db_session.execute(
        select(func.count()).where(Source.user_id == mock_user["user_id"])
    )
    assert sources_count.scalar() == 0

    qdrant_count = await qdrant_adapter.count(tenant_id=mock_user["user_id"])
    assert qdrant_count == 0
```

---

## Unit Test Patterns

```python
# tests/unit/services/test_conflict_service.py
from unittest.mock import AsyncMock, MagicMock
from src.services.conflict_service import ConflictService

class TestConflictService:

    def test_auto_resolve_high_authority_differential(self):
        """When challenger authority > incumbent by 3+, auto-resolve."""
        service = ConflictService()
        result = service.should_auto_resolve(
            challenger_authority=8,
            incumbent_authority=4,
        )
        assert result is True

    def test_no_auto_resolve_low_differential(self):
        """Authority diff < 3 → manual resolution required."""
        service = ConflictService()
        result = service.should_auto_resolve(
            challenger_authority=6,
            incumbent_authority=5,
        )
        assert result is False

    async def test_resolve_accept_new_updates_neo4j(self, mock_neo4j):
        """ACCEPT_NEW: old memory is_valid=False, SUPERSEDES edge created."""
        mock_neo4j.run_query = AsyncMock(return_value=None)
        service = ConflictService(neo4j_adapter=mock_neo4j)

        await service.resolve(
            conflict_id="test-conflict",
            action="ACCEPT_NEW",
            tenant_id="test-user",
        )

        # Assert Neo4j write called with SUPERSEDES relationship
        call_args = mock_neo4j.run_query.call_args
        assert "SUPERSEDES" in call_args[0][0]  # Cypher query
```

---

## Frontend Testing (Vitest + Playwright)

```typescript
// tests/unit/hooks/use-keyboard-inbox.test.ts
import { renderHook, act } from "@testing-library/react";
import { useKeyboardInbox } from "@/hooks/use-keyboard-inbox";

describe("useKeyboardInbox", () => {
  it("fires 'accept' on Enter keypress", () => {
    const onAction = vi.fn();
    renderHook(() => useKeyboardInbox(onAction, true));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });

    expect(onAction).toHaveBeenCalledWith("accept");
  });

  it("does not fire when disabled", () => {
    const onAction = vi.fn();
    renderHook(() => useKeyboardInbox(onAction, false));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "j" }));
    });

    expect(onAction).not.toHaveBeenCalled();
  });
});
```

```typescript
// e2e/inbox.spec.ts (Playwright)
import { test, expect } from "@playwright/test";

test("Memory Inbox binary triage flow", async ({ page }) => {
  await page.goto("/inbox");
  
  // Verify conflict card visible
  await expect(page.locator("[data-testid='conflict-card']").first()).toBeVisible();
  
  // Press J to advance, Enter to accept
  await page.keyboard.press("j");
  await page.keyboard.press("Enter");
  
  // Toast should appear
  await expect(page.locator(".sonner-toast")).toBeVisible();
  await expect(page.locator(".sonner-toast")).toContainText("Updated");
});
```

---

## CI Configuration (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: make quality   # ruff + pyright

  test:
    runs-on: ubuntu-latest
    needs: quality
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_DB: test, POSTGRES_USER: test, POSTGRES_PASSWORD: test}
        options: --health-cmd pg_isready
      redis:
        image: redis:7-alpine
        options: --health-cmd "redis-cli ping"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --dev
      - run: uv run pytest tests/ -n auto --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: 20}
      - run: npm ci
      - run: npm run build   # TypeScript check + Next.js build
      - run: npm run test    # Vitest unit tests
```

---

## Running Tests Locally

```bash
# Backend — all tests
make test

# Backend — fast unit tests only (no Docker needed)
uv run pytest tests/unit/ -n auto -q

# Backend — specific test file
uv run pytest tests/integration/api/test_ingest_endpoints.py -v

# Backend — with coverage report
uv run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Frontend — unit tests
npm run test

# Frontend — install Playwright browsers (one-time, required before first E2E run):
npx playwright install
# Or for CI, only install Chromium:
npx playwright install chromium

# Frontend — E2E tests (requires running app + browsers installed):
npm run dev &
npx playwright test

# Frontend — E2E in headed mode (to watch the tests run):
npx playwright test --headed

# Full CI check before PR
make ci-local   # = make quality + make test

# E2E tests (requires Playwright browsers installed + app running):
npx playwright test

# E2E in headed mode (watch the browser):
npx playwright test --headed

# Install browsers once (required before first E2E run):
npx playwright install chromium
```

---

## E2E Business Logic Tests (Playwright — Revenue-Critical Path)

The E2E suite lives in `ravenbase-web/e2e/` and tests the paths that make money.
Unit tests verify logic; E2E tests verify the business still works after every deploy.

### Setup

```typescript
// playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // Revenue tests run sequentially to avoid state conflicts
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
```

```bash
# .env.test (ravenbase-web) — points to staging, never production
PLAYWRIGHT_BASE_URL=https://staging.ravenbase.app
NEXT_PUBLIC_API_URL=https://staging-api.ravenbase.app
# Use a dedicated Clerk test instance or staging app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_STAGING_KEY
```

### Auth Fixture

```typescript
// e2e/fixtures/auth.ts
import { test as base } from "@playwright/test";

// Use Clerk's programmatic sign-in to bypass CAPTCHA and OTP
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // Sign in via Clerk API (testing token or staging credentials)
    await page.goto("/sign-in");
    await page.fill("[name=identifier]", process.env.E2E_TEST_EMAIL!);
    await page.click("[data-locator='continue']");
    await page.fill("[name=password]", process.env.E2E_TEST_PASSWORD!);
    await page.click("[data-locator='continue']");
    await page.waitForURL("**/chat**");
    await use(page);
  },
});
```

### Core Revenue Loop Test

```typescript
// e2e/core-revenue.spec.ts
import { test, expect } from "./fixtures/auth";
import path from "path";

test("core revenue loop: upload → process → generate → credit deducted", async ({
  authenticatedPage: page,
}) => {
  // 1. Check starting credit balance
  const balanceBefore = await page.locator("[data-testid='credit-balance']").textContent();
  const creditsBefore = parseInt(balanceBefore!.replace(/\D/g, ""), 10);

  // 2. Upload a small fixture PDF
  await page.goto("/sources");
  const fileInput = page.locator("input[type='file']");
  await fileInput.setInputFiles(path.join(__dirname, "fixtures/test-invoice.pdf"));

  // 3. Wait for SSE progress to reach 100% completed
  await expect(page.locator("[data-testid='ingestion-status']")).toHaveText("completed", {
    timeout: 90_000, // 90s SLA for a small PDF
  });

  // 4. Navigate to Workstation and generate a Meta-Document
  await page.goto("/workstation");
  await page.fill("[data-testid='prompt-input']", "Summarize the key facts in this document.");
  await page.keyboard.press("Enter");

  // 5. Wait for streaming to complete
  await expect(page.locator("[data-testid='generation-status']")).toHaveText("done", {
    timeout: 60_000,
  });

  // 6. Assert credits decreased by exactly 18 (Claude Haiku default cost)
  const balanceAfter = await page.locator("[data-testid='credit-balance']").textContent();
  const creditsAfter = parseInt(balanceAfter!.replace(/\D/g, ""), 10);
  expect(creditsBefore - creditsAfter).toBe(18);
});
```

### Stripe Checkout Test

```typescript
// e2e/stripe-checkout.spec.ts
import { test, expect } from "./fixtures/auth";

test("stripe checkout: Get Pro button generates checkout URL", async ({
  authenticatedPage: page,
}) => {
  await page.goto("/pricing");

  // Intercept the redirect to Stripe
  const [stripeRedirect] = await Promise.all([
    page.waitForURL("**/checkout.stripe.com/**", { timeout: 10_000 }),
    page.click("[data-testid='get-pro-button']"),
  ]);

  // Assert we landed on Stripe Checkout with a valid session
  expect(page.url()).toContain("checkout.stripe.com");
  expect(page.url()).toContain("/pay/cs_");
});
```

### CI/CD Blocker

Add the following `e2e` job to `.github/workflows/ci.yml`. Merges to `main` are
blocked if the E2E core revenue test fails:

```yaml
  e2e:
    runs-on: ubuntu-latest
    needs: [quality, test, frontend]
    environment: staging  # Uses staging secrets (PLAYWRIGHT_BASE_URL, etc.)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npx playwright install chromium
      - run: npx playwright test e2e/core-revenue.spec.ts
        env:
          PLAYWRIGHT_BASE_URL: ${{ secrets.STAGING_URL }}
          E2E_TEST_EMAIL: ${{ secrets.E2E_TEST_EMAIL }}
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

> **Note:** `e2e/fixtures/test-invoice.pdf` must be committed to the repo — a minimal
> valid PDF (< 100KB) used as the fixture upload. Never use a real document.

> **Scope:** Only `core-revenue.spec.ts` is a CI blocker. `stripe-checkout.spec.ts` runs
> in CI but is allowed to fail (Stripe staging is external infrastructure outside your control).
