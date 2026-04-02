# STORY-027: Conversational Memory Chat — Frontend

**Epic:** EPIC-09 — Memory Intelligence
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-026 (backend chat endpoints must exist and client regenerated)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-12-AC-1: POST /v1/chat/sessions creates a new session
- FR-12-AC-2: POST /v1/chat/sessions/{id}/message streams response via SSE with citations
- FR-12-AC-3: Citations reference specific Memory node IDs
- FR-12-AC-4: Multi-turn context preserved within session
- FR-12-AC-5: Credits deducted per message

## Component
COMP-04: GenerationEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (the frontend CLAUDE.md in this repo root) — all frontend rules
> 2. `docs/design/CLAUDE_FRONTEND.md` — useApiFetch (client components), approved packages
> 3. `docs/design/01-design-system.md` — color tokens, typography, dark mode dashboard rules
> 4. `docs/design/02-component-library.md` — shadcn components to use (ScrollArea, Separator, Badge)
> 5. `docs/stories/EPIC-05-metadoc/STORY-017.md` — SSE streaming pattern via use-sse.ts hook

---

## User Story
As a user, I want a chat interface where I can ask questions about my knowledge base
and receive streamed answers with citations linking back to my source memories.

## Context
- API: uses STORY-026's `/v1/chat/message` (streaming SSE) and `/v1/chat/sessions` endpoints
- SSE: reuses `hooks/use-sse.ts` hook created in STORY-007
- Citations: each AI response includes `citations[]` — clicking opens Graph Explorer node panel
- Sessions: persisted in backend; sidebar shows history

## Acceptance Criteria
- [ ] AC-1: `/chat` page renders with sidebar (session list) + main chat area
- [ ] AC-2: User types a message, presses Enter or clicks Send — tokens stream in real-time
- [ ] AC-3: First SSE event `{type: "session"}` captures `session_id` stored in component state
- [ ] AC-4: AI message bubble appears immediately and fills token-by-token (streaming cursor ▌)
- [ ] AC-5: Final `{type: "done"}` event renders citation footnotes below the message
- [ ] AC-6: Clicking a citation opens the Graph Explorer with that node highlighted (route: `/graph?node={memory_id}`)
- [ ] AC-7: Sidebar shows all past sessions (title = first 60 chars of first message); click to load and resume
- [ ] AC-8: Model selector (Haiku / Sonnet) shows credit cost next to each option
- [ ] AC-9: Insufficient credits: `402` response shows upgrade prompt modal (not a console error)
- [ ] AC-10: Empty state (no sessions yet): "Ask me anything about your memories. I'll search your knowledge base and answer with citations."
- [ ] AC-11: Mobile (< 768px): session sidebar hidden by default; accessible via a
  history icon button in the chat header that opens a Sheet drawer
- [ ] AC-12: Mobile (< 768px): message input fixed to bottom with safe-area padding;
  send button always visible without scrolling; uses `h-[100dvh]` not `h-screen`

## Technical Notes

### Files to Create
- `app/(dashboard)/chat/page.tsx` — page layout (server component, dark mode)
- `components/domain/MemoryChat.tsx` — main client component (`"use client"`)
- `components/domain/ChatSessionSidebar.tsx` — session history list
- `components/domain/ChatMessage.tsx` — individual message bubble with citations
- `components/domain/CitationCard.tsx` — citation link that navigates to graph node

### Mobile Layout

```tsx
{/* Chat page mobile layout */}
<div className="flex h-[100dvh] flex-col">  {/* dvh avoids iOS address-bar jump */}
  {/* Header with history toggle on mobile */}
  <header className="flex items-center justify-between p-4 border-b">
    <h1 className="font-serif text-lg">Chat</h1>
    <Button variant="ghost" size="icon" className="md:hidden"
      onClick={() => setSessionsOpen(true)}>
      <History className="w-5 h-5" />
    </Button>
  </header>
  {/* Messages — scrollable */}
  <div className="flex-1 overflow-y-auto p-4 space-y-4">
    {messages.map(msg => <ChatMessage key={msg.id} message={msg} />)}
  </div>
  {/* Input — sticky bottom with iOS safe area */}
  <div className="sticky bottom-0 p-4 border-t bg-background
                  pb-[max(1rem,env(safe-area-inset-bottom))]">
    <ChatInput />
  </div>
</div>
```

Use `h-[100dvh]` (dynamic viewport height) NOT `h-screen` — `h-screen` causes the
iOS Safari address bar jump that makes the layout shift during scroll.

### Architecture Constraints
- `MemoryChat.tsx` MUST be `"use client"` — uses EventSource + state + useApiFetch
- SSE token: use `new EventSource(url)` directly (not via apiFetch) — EventSource is browser-native
- Token must be appended as query param: `?token={clerkToken}` (EventSource cannot set headers)
- Use `useApiFetch()` hook for non-streaming calls (session list, session load, delete)
- Citation click: use Next.js `router.push('/graph?node=${memory_id}')` — do not use `<a>` tags
- No `<form>` tags — chat input is a `<textarea>` with `onKeyDown` handler for Enter key
- Textarea: Enter sends, Shift+Enter inserts newline
- Model selector: shadcn `<Select>` component

### Chat Component State Machine

```typescript
// components/domain/MemoryChat.tsx
"use client";
type ChatState = "idle" | "streaming" | "error";
type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
};

// State:
const [messages, setMessages] = useState<Message[]>([]);
const [sessionId, setSessionId] = useState<string | null>(null);
const [chatState, setChatState] = useState<ChatState>("idle");
const [input, setInput] = useState("");
const [model, setModel] = useState<"haiku" | "sonnet">("haiku");
```

### SSE Streaming Pattern (chat-specific)

```typescript
// Inside handleSend() in MemoryChat.tsx
const handleSend = async () => {
  if (!input.trim() || chatState === "streaming") return;
  const userMessage = input.trim();
  setInput("");
  setChatState("streaming");

  // Add user message immediately (optimistic)
  const userMsgId = crypto.randomUUID();
  setMessages(prev => [...prev, { id: userMsgId, role: "user", content: userMessage }]);

  // Add empty assistant message with streaming cursor
  const asstMsgId = crypto.randomUUID();
  setMessages(prev => [...prev, { id: asstMsgId, role: "assistant", content: "", isStreaming: true }]);

  const token = await getToken();  // from useAuth()
  const url = `${process.env.NEXT_PUBLIC_API_URL}/v1/chat/message`;

  // Use fetch (not EventSource) for POST streaming
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message: userMessage, session_id: sessionId, profile_id: activeProfileId, model }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const lines = chunk.split("\n").filter(l => l.startsWith("data:"));
    for (const line of lines) {
      const event = JSON.parse(line.slice(5).trim());
      if (event.type === "session") setSessionId(event.session_id);
      if (event.type === "token") {
        setMessages(prev => prev.map(m =>
          m.id === asstMsgId ? { ...m, content: m.content + event.content } : m
        ));
      }
      if (event.type === "done") {
        setMessages(prev => prev.map(m =>
          m.id === asstMsgId ? { ...m, citations: event.citations, isStreaming: false } : m
        ));
        setChatState("idle");
      }
      if (event.type === "error") {
        setChatState("error");
      }
    }
  }
};
```

### Citation Card Pattern

```tsx
// components/domain/CitationCard.tsx
import { useRouter } from "next/navigation";

export function CitationCard({ citation }: { citation: Citation }) {
  const router = useRouter();
  return (
    <button
      onClick={() => router.push(`/graph?node=${citation.memory_id}`)}
      className="text-xs font-mono text-muted-foreground border border-border
                 rounded px-2 py-0.5 hover:border-primary hover:text-primary
                 transition-colors"
    >
      ↗ {citation.source_filename}
    </button>
  );
}
```

### Sidebar Navigation Entry
Add to `app/(dashboard)/layout.tsx` sidebar items:
```tsx
{ icon: MessageSquare, label: "Chat", href: "/chat" }
// Place between Graph Explorer and Memory Inbox in the nav
```

## Definition of Done
- [ ] Chat page renders at `/chat` in dark mode
- [ ] Sending a message streams tokens in real-time (visible token-by-token)
- [ ] Multi-turn: second message in same session has context of first
- [ ] Citations render as clickable cards after each AI message
- [ ] Clicking citation navigates to Graph Explorer with node context
- [ ] Session history loads in sidebar; clicking resumes the session
- [ ] Mobile: input fixed to bottom, sessions in drawer
- [ ] `npm run build` passes (0 TypeScript errors)
- [ ] `npm run test` passes

## Final Localhost Verification (mandatory before marking complete)

After `npm run build` passes and all tests pass, verify the running application works:

**Step 1 — Clear stale cache:**
```bash
rm -rf .next
```

**Step 2 — Start dev server:**
```bash
npm run dev
```

**Step 3 — Verify no runtime errors:**
- Open http://localhost:3000 in the browser
- Sign in if redirected to /login
- Navigate to `/chat`
- Confirm NO "Internal Server Error" or webpack runtime errors
- Confirm CSS loads correctly (no unstyled content)
- Open browser DevTools → Console tab
- Confirm no red errors (yellow warnings acceptable)

**Step 4 — Report one of:**
- ✅ `localhost verified` — page renders correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

## Testing This Story

```bash
# Build check:
npm run build
# Expected: 0 TypeScript errors

# Manual test:
# 1. Navigate to localhost:3000/chat
# 2. Type "What Python projects have I worked on?"
# 3. Verify: tokens appear one by one (streaming cursor visible)
# 4. Verify: citation cards appear after response completes
# 5. Click a citation — verify Graph Explorer opens with that node
# 6. Send a follow-up message — verify session_id is the same (multi-turn)
# 7. Refresh page — verify session appears in sidebar
# 8. Click session in sidebar — verify full conversation loads
# 9. Resize to 375px — verify input is fixed at bottom, sessions in drawer
```

**Passing result:** Chat streams in real-time. Citations link to graph nodes. Multi-turn context works. Session history persists.

---

## Agent Implementation Brief

```
Implement STORY-027: Conversational Memory Chat — Frontend.
Backend is complete. Run npm run generate-client first.

Read first:
1. CLAUDE.md (frontend rules in this repo root)
2. docs/design/AGENT_DESIGN_PREAMBLE.md — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX.
3. docs/design/00-brand-identity.md — logo spec, voice rules, mono label pattern
4. docs/design/01-design-system.md — all color tokens, typography
5. docs/design/CLAUDE_FRONTEND.md (useApiFetch hook, no form tags, approved packages)
6. docs/stories/EPIC-02-ingestion/STORY-007.md (SSE streaming pattern reference)
7. docs/stories/EPIC-09-memory-intelligence/STORY-027.md (this file)

Key constraints:
- "use client" on MemoryChat.tsx — uses state, EventSource, useAuth
- Use fetch() with streaming reader for POST SSE (EventSource only supports GET)
- No <form> tags — textarea with onKeyDown for Enter
- Enter sends, Shift+Enter inserts newline
- Citation click uses router.push() — not <a href>
- Token: get from useAuth().getToken() — client component pattern

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
npm run build && npm run test

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-027 conversational memory chat frontend"
git push

# 3. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-027
git add docs/stories/epics.md && git commit -m "docs: mark STORY-027 complete"
```
