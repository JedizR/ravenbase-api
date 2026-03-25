# STORY-028: AI Chat Context Import Helper

**Epic:** EPIC-09 — Memory Intelligence
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-005 (upload endpoint), STORY-008 (text ingestion endpoint)

---

> **⚠️ This story spans BOTH repos. Work backend first:**
>
> **Part 1 — Backend** (`ravenbase-api/`): `GET /v1/ingest/import-prompt` endpoint
> → Complete Part 1 first. Merge it. Run `npm run generate-client` in the web repo.
>
> **Part 2 — Frontend** (`ravenbase-web/`): Import Helper UI with generated prompt + paste area
> → Only start Part 2 after Part 1 is confirmed working.
>
> **In the backend session:** Use the "Backend Agent Brief" at the bottom of this story.
> **In the frontend session:** Use the "Frontend Agent Brief" at the bottom of this story.

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/architecture/02-database-schema.md` — Concept node structure in Neo4j (for context extraction)
> 3. `docs/architecture/03-api-contract.md` — `/v1/ingest/text` existing endpoint to reuse
> 4. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (for Part 2)
> 5. `docs/design/02-component-library.md` — shadcn components (Tabs, Textarea, Button, Badge)

---

## User Story
As a user, I want a guided UI to extract context from any AI chat (ChatGPT, Claude,
Gemini, or others) and ingest it into Ravenbase, so that my knowledge base stays current
with conversations I have across different platforms.

## Context
- **The problem this solves:** Claude/ChatGPT don't offer conversation exports that Docling
  can parse. Instead of a parser, Ravenbase gives the user a smart extraction prompt to run
  inside their AI chat, then paste the structured response back. Human-in-the-loop by design.
- **Backend:** One new endpoint that generates a customized extraction prompt based on the
  user's existing knowledge graph concepts. Knows what to ask for.
- **Frontend:** Two-panel ingestion UI: (1) file upload dropzone (existing), (2) AI chat
  import helper (new). Both live on `/dashboard/sources` as tabs.

## Acceptance Criteria
- [ ] AC-1: `GET /v1/ingest/import-prompt?profile_id=` returns `{prompt_text, detected_concepts[]}` — the extraction prompt is personalized based on the user's existing Neo4j Concept nodes
- [ ] AC-2: If the user has no concepts yet (new user), the endpoint returns a generic extraction prompt (not a 404)
- [ ] AC-3: Frontend: `/dashboard/sources` has two tabs: "Upload Files" (existing) and "Import from AI Chat" (new)
- [ ] AC-4: "Import from AI Chat" tab shows: (1) generated extraction prompt in a read-only textarea with one-click Copy button, (2) numbered instructions panel, (3) large paste-back textarea, (4) Submit button
- [ ] AC-5: Copy button copies the prompt text and shows "Copied ✓" feedback for 2 seconds (using Clipboard API)
- [ ] AC-6: User pastes AI response into the paste-back textarea → Submit → calls `/v1/ingest/text` → shows same SSE progress as file upload
- [ ] AC-7: Instructions panel is clear and non-technical: "1. Copy the prompt above 2. Open ChatGPT, Claude, or any AI 3. Paste the prompt and send it 4. Copy the AI's full response 5. Paste it below and click Import"
- [ ] AC-8: Profile selector dropdown in the Import tab — user chooses which System Profile to import into
- [ ] AC-9: Text input area accepts up to 100,000 characters (large AI responses are common)
- [ ] AC-10: `GET /v1/ingest/import-prompt` requires auth; returns 401 without token
- [ ] AC-11: Mobile (375px): both tabs render without horizontal overflow; generated
  prompt textarea is scrollable with `max-h-40 overflow-y-auto` on mobile

## Technical Notes

### Backend Files to Create
- `src/api/routes/ingest.py` — add `GET /v1/ingest/import-prompt` endpoint
- `src/schemas/ingest.py` — add `ImportPromptResponse` Pydantic schema
- `src/services/ingestion_service.py` — add `generate_import_prompt(tenant_id, profile_id)` method

### Frontend Files to Create/Modify
- `app/(dashboard)/sources/page.tsx` — add Tabs wrapper (Upload / Import from AI Chat)
- `components/domain/ImportFromAIChat.tsx` — new import helper tab content
- `components/domain/GeneratedPromptBox.tsx` — read-only textarea + Copy button

### Backend: Import Prompt Generation

```python
# src/services/ingestion_service.py
async def generate_import_prompt(
    self,
    tenant_id: str,
    profile_id: str | None,
    neo4j_adapter: Neo4jAdapter,
) -> ImportPromptResponse:
    """Generate a personalized extraction prompt based on existing concepts."""
    # Fetch existing concepts from Neo4j
    concepts = await neo4j_adapter.run_query(
        """
        MATCH (c:Concept {tenant_id: $tenant_id})
        WHERE ($profile_id IS NULL OR c.profile_id = $profile_id)
        RETURN c.name AS name, c.type AS type
        ORDER BY c.last_seen DESC
        LIMIT 30
        """,
        tenant_id=tenant_id,
        profile_id=profile_id,
    )

    concept_names = [c["name"] for c in concepts] if concepts else []

    if concept_names:
        concept_list = ", ".join(concept_names[:20])
        focus_line = f"Focus especially on these topics that are already in my knowledge base: {concept_list}."
    else:
        focus_line = "Summarize all key topics, decisions, and learnings from this conversation."

    prompt_text = f"""Please analyze this conversation and extract a structured knowledge summary.

{focus_line}

For each topic found, provide:
- **Topic:** [name]
- **Key facts:** [bullet points of specific facts, decisions, or learnings]
- **Tools/technologies:** [if applicable]
- **Timeline:** [approximate dates or sequence if mentioned]
- **Status:** [current/past/planned]

Be specific and factual. Include concrete details like project names, technology versions,
outcomes, and decisions made. Omit pleasantries and filler. Output only the structured summary."""

    return ImportPromptResponse(
        prompt_text=prompt_text,
        detected_concepts=concept_names[:20],
    )
```

### Backend: API Endpoint

```python
# src/api/routes/ingest.py — add to existing router
@router.get("/import-prompt", response_model=ImportPromptResponse)
async def get_import_prompt(
    profile_id: str | None = Query(default=None),
    user: dict = Depends(require_user),
) -> ImportPromptResponse:
    """Return a personalized extraction prompt for importing AI chat context."""
    return await ingestion_service.generate_import_prompt(
        tenant_id=user["user_id"],
        profile_id=profile_id,
        neo4j_adapter=neo4j_adapter,
    )
```

### Frontend: GeneratedPromptBox Component

```tsx
// components/domain/GeneratedPromptBox.tsx
"use client";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Check, Copy } from "lucide-react";

export function GeneratedPromptBox({ promptText }: { promptText: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(promptText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative">
      <Textarea
        value={promptText}
        readOnly
        className="font-mono text-xs min-h-[200px] resize-none bg-secondary/50"
      />
      <Button
        size="sm"
        variant="outline"
        onClick={handleCopy}
        className="absolute top-2 right-2"
      >
        {copied ? (
          <><Check className="w-3 h-3 mr-1" /> Copied</>
        ) : (
          <><Copy className="w-3 h-3 mr-1" /> Copy</>
        )}
      </Button>
    </div>
  );
}
```

### Mobile

Both tabs work at 375px. The generated prompt textarea needs height cap on mobile:

```tsx
<Textarea
  value={promptText}
  readOnly
  className="font-mono text-xs resize-none
             h-32 md:min-h-[200px]
             overflow-y-auto"
/>
```

### Architecture Constraints
- `GET /v1/ingest/import-prompt` is a read-only endpoint — no data mutation
- Prompt generation must handle `concepts = []` gracefully (new user with no graph yet)
- Frontend Submit button calls existing `/v1/ingest/text` — no new endpoint for this
- Text input area: `maxLength={100000}` on textarea — large AI responses expected
- Instructions use plain language — non-technical users must understand

## Definition of Done
- [ ] `GET /v1/ingest/import-prompt` returns personalized prompt with concept list
- [ ] New user (no concepts): endpoint returns generic prompt (not error)
- [ ] Frontend tabs work: Upload Files / Import from AI Chat
- [ ] Copy button works with Clipboard API + 2-second feedback
- [ ] Paste + Submit calls `/v1/ingest/text` and shows progress
- [ ] `make quality` + `make test` pass (backend)
- [ ] `npm run build` passes (frontend)

## Testing This Story

```bash
# Backend:
TOKEN="your_token"
# User with existing concepts:
curl "http://localhost:8000/v1/ingest/import-prompt?profile_id=your-profile-uuid" \
  -H "Authorization: Bearer ${TOKEN}"
# Expected: {"prompt_text": "...Focus especially on: TypeScript, Python, ML...", "detected_concepts": [...]}

# New user (no concepts):
curl "http://localhost:8000/v1/ingest/import-prompt" \
  -H "Authorization: Bearer ${TOKEN}"
# Expected: {"prompt_text": "...Summarize all key topics...", "detected_concepts": []}

# Frontend:
# 1. Navigate to /dashboard/sources
# 2. Click "Import from AI Chat" tab
# 3. Verify prompt textarea shows personalized prompt
# 4. Click Copy — verify "Copied ✓" appears for 2 seconds
# 5. Paste sample text in the paste area
# 6. Click Import — verify progress bar appears
# make quality && npm run build
```

---

## Backend Agent Brief (for ravenbase-api/ session)

```
Implement STORY-028 Part 1 (Backend): Import prompt generation endpoint.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/architecture/02-database-schema.md (Concept nodes in Neo4j)
3. docs/architecture/03-api-contract.md (existing /v1/ingest/* endpoints)
4. docs/stories/EPIC-09-memory-intelligence/STORY-028.md (this file)

Key constraints:
- Add GET /v1/ingest/import-prompt to existing ingest router
- Read Concept nodes from Neo4j scoped by tenant_id AND profile_id
- Handle empty concepts list gracefully (new user — return generic prompt)
- This is a read-only endpoint — no data mutations, no ARQ jobs

Show plan first. Do not implement yet.
```

## Frontend Agent Brief (for ravenbase-web/ session — after backend Part 1 merged)

```
Implement STORY-028 Part 2 (Frontend): AI Chat Import Helper UI.
Backend endpoint is deployed. Run npm run generate-client first.

Read first:
1. CLAUDE.md (frontend rules in this repo root)
2. docs/design/CLAUDE_FRONTEND.md (useApiFetch, no form tags, approved packages)
3. docs/design/02-component-library.md (Tabs, Textarea, Button, Badge components)
4. docs/stories/EPIC-09-memory-intelligence/STORY-028.md (this file)

Key constraints:
- Add Tabs to /dashboard/sources/page.tsx (Upload Files | Import from AI Chat)
- Clipboard API in GeneratedPromptBox — no third-party clipboard package needed
- Textarea maxLength={100000} — large AI responses expected
- Submit calls existing /v1/ingest/text endpoint — no new endpoint needed
- No <form> tags — use onClick handlers

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# Backend Part 1:
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-028 import prompt backend endpoint"
git push
# Regenerate client:
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-028"
git push && cd ../ravenbase-api

# Frontend Part 2:
npm run build && npm run test
git add -A && git commit -m "feat(ravenbase): STORY-028 AI chat import helper UI"
git push

# Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-028
```
