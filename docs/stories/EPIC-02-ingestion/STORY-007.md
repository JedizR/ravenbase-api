# STORY-007: SSE Progress Stream (Redis pub/sub)

**Epic:** EPIC-02 — Ingestion Pipeline
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-005
**Type:** Cross-repo
**Repo:** ravenbase-api + ravenbase-web

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-01-AC-6: Progress published to Redis pub/sub at each status transition (SSE stream to client)

## Component
COMP-01: IngestionPipeline

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/architecture/04-background-jobs.md` — SSE section, Redis pub/sub pattern
> 3. `docs/architecture/03-api-contract.md` — `GET /v1/ingest/stream/{source_id}` spec
> 4. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (apiFetch, no form tags, Tailwind only)
> 5. `docs/design/02-component-library.md` — Progress + Skeleton component patterns

> **This story spans BOTH repos. Always work backend first:**
>
> **Part 1 — Backend** (`ravenbase-api/`): SSE endpoint + Redis pub/sub subscriber
> → Complete Part 1 first. Merge it. Run `npm run generate-client` in the web repo.
>
> **Part 2 — Frontend** (`ravenbase-web/`): `IngestionProgress` component + `use-sse.ts` hook
> → Only start Part 2 after Part 1 is confirmed working.
>
> **In the backend session:** Use the "Backend Agent Brief" at the bottom of this story.
> **In the frontend session:** Use the "Frontend Agent Brief" at the bottom of this story.

---

## User Story
As a user, I want to see real-time progress updates as my file is being processed so I know the system is working.

## Context
- SSE pattern: `architecture/04-background-jobs.md` — SSE section
- API contract: `architecture/03-api-contract.md` — `GET /v1/ingest/stream/{source_id}`

## Acceptance Criteria
- [x] AC-1: `GET /v1/ingest/stream/{source_id}?token=` returns `text/event-stream`
- [x] AC-2: Token validated via `verify_token_query_param` (Clerk JWT as query param)
- [x] AC-3: SSE stream emits `data:` events with `{progress_pct, message, status}`
- [x] AC-4: Stream closes automatically when status is `completed` or `failed`
- [x] AC-5: Client that disconnects mid-stream does not cause server error (test with connection abort)
- [ ] AC-6: Frontend `IngestionProgress` component subscribes to SSE and updates progress bar in real-time
- [ ] AC-7: Frontend shows correct states: idle → uploading → processing (with %) → complete / error

## Technical Notes

### Backend Files to Create (ravenbase-api — Part 1)
- `src/api/routes/ingest.py` — add `GET /v1/ingest/stream/{source_id}` SSE endpoint
- `src/api/dependencies/auth.py` — add `verify_token_query_param` for EventSource auth

### Frontend Files to Create (ravenbase-web — Part 2, after client regenerated)
- `components/domain/IngestionProgress.tsx` — SSE subscriber + shadcn Progress bar
- `hooks/use-sse.ts` — reusable SSE hook (also used by Workstation in STORY-017)

### Architecture Constraints
- SSE endpoint MUST use `sse-starlette` (already in pyproject.toml — no new packages)
- Token passed as query param (`?token=`) because `EventSource` cannot set headers
- Disconnect handling: wrap Redis subscribe loop in `try/finally` — always call `pubsub.unsubscribe()`
- Stream MUST close when `status === "completed"` or `status === "failed"` to prevent memory leaks

### SSE Backend Pattern
```python
# src/api/routes/ingest.py
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, Query, Depends
import json

@router.get("/stream/{source_id}")
async def stream_progress(
    source_id: str,
    token: str = Query(...),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    user = await verify_token_query_param(token)

    async def event_generator():
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"job:progress:{source_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield {"data": json.dumps(data)}
                    if data["status"] in ("completed", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(f"job:progress:{source_id}")

    return EventSourceResponse(event_generator())
```

### Frontend SSE Pattern
```typescript
// components/domain/IngestionProgress.tsx
"use client";
import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";

interface ProgressEvent {
  progress_pct: number;
  message: string;
  status: string;
}

export function IngestionProgress({ sourceId }: { sourceId: string }) {
  const [progress, setProgress] = useState<ProgressEvent | null>(null);

  useEffect(() => {
    const token = getClerkToken(); // from Clerk frontend SDK
    const es = new EventSource(
      `/api/v1/ingest/stream/${sourceId}?token=${token}`
    );
    es.onmessage = (e) => {
      const data: ProgressEvent = JSON.parse(e.data);
      setProgress(data);
      if (data.status === "completed" || data.status === "failed") {
        es.close();
      }
    };
    return () => es.close();
  }, [sourceId]);

  if (!progress) return <Skeleton className="h-2 w-full" />;
  return (
    <div className="space-y-1">
      <Progress value={progress.progress_pct} />
      <p className="text-xs text-muted-foreground">{progress.message}</p>
    </div>
  );
}
```

## Definition of Done
- [ ] SSE stream emits events at each ingestion stage
- [ ] Stream auto-closes on completed/failed status
- [ ] Client disconnect does not cause server error or memory leak
- [ ] `IngestionProgress` component updates in real-time
- [ ] `make quality` + `npm run build` pass

## Testing This Story

```bash
# Backend SSE test:
uv run pytest tests/integration/api/test_ingest_stream.py -v

# Manual SSE test (requires running worker + Redis):
TOKEN="your_clerk_token"
SOURCE_ID="your_source_uuid"
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8000/v1/ingest/stream/${SOURCE_ID}?token=${TOKEN}"
# Expected: data: {"progress_pct": 0, "message": "Parsing document...", "status": "processing"}
#           data: {"progress_pct": 50, "message": "Generating embeddings...", "status": "processing"}
#           data: {"progress_pct": 100, "message": "Complete", "status": "completed"}
# Then stream closes.

# Frontend build:
npm run build
```

**Passing result:** SSE stream emits progress events at each stage and closes automatically on completion. Frontend progress bar updates in real-time.

---

## Backend Agent Brief (for ravenbase-api/ session)

```
Implement STORY-007 Part 1 (Backend): SSE progress stream.
This is the backend half only. Do NOT implement frontend components.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/architecture/04-background-jobs.md (Redis pub/sub + SSE pattern)
3. docs/architecture/03-api-contract.md (GET /v1/ingest/stream/{source_id} spec)
4. docs/stories/EPIC-02-ingestion/STORY-007.md (this file)

Constraints:
- SSE uses sse-starlette (already approved)
- Token passed as query param ?token= (EventSource cannot set headers)
- Wrap Redis subscribe in try/finally — always unsubscribe on disconnect

Show plan first. Do not implement yet.
```

## Frontend Agent Brief (for ravenbase-web/ session — only after backend Part 1 merged)

```
Implement STORY-007 Part 2 (Frontend): IngestionProgress component.
The backend SSE endpoint is deployed. Run npm run generate-client first.

Read first:
1. CLAUDE.md (the frontend CLAUDE.md in this repo root)
2. docs/design/CLAUDE_FRONTEND.md (useApiFetch, "use client" rules)
3. docs/design/02-component-library.md (Progress + Skeleton patterns)
4. docs/stories/EPIC-02-ingestion/STORY-007.md (this file)

Constraints:
- EventSource connects directly (not via apiFetch — EventSource is browser-native)
- Token appended as query param: new EventSource(`/v1/ingest/stream/${id}?token=${token}`)
- Use the use-sse.ts hook pattern (defined in this story's Technical Notes)

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
git add -A && git commit -m "feat(ravenbase): STORY-007 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-007"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-007
git add docs/stories/epics.md && git commit -m "docs: mark STORY-007 complete"
```
