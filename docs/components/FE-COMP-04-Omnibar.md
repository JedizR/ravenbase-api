# Omnibar

> **Component ID:** FE-COMP-04
> **Epic:** EPIC-02 — Ingestion Pipeline, EPIC-06 — Authentication & System Profiles
> **Stories:** STORY-008, STORY-020
> **Type:** Frontend (Dashboard)

---

## Purpose

The Omnibar is the central keyboard-driven command interface for Ravenbase. It opens on `Cmd+K` / `Ctrl+K` and provides slash commands for quick actions without navigating menus. The two core commands: `/ingest [text]` captures text to the active profile, `/profile` switches the active System Profile. Other commands (`/search`, `/generate`) exist in the UI but are currently not implemented (BUG-021).

---

## User Journey

**Text ingest flow:**
1. User on any dashboard page → `Cmd+K` (Mac) or `Ctrl+K` (Windows)
2. Omnibar opens centered at top of viewport
3. Types: `/ingest My meeting today was about the React migration`
4. Presses Enter
5. `POST /v1/ingest/text {content: "...", profile_id: activeProfileId}`
6. Toast: "◆ CAPTURED — Added to [Profile Name]"
7. Cost: 0 credits (text ingest is always free — no admin bypass needed)
8. Omnibar closes

**Profile switch flow:**
1. `Cmd+K` → types `/profile`
2. Dropdown shows all profiles with active profile highlighted (✓ checkmark)
3. Arrow keys navigate, Enter selects
4. `ProfileContext.setActiveProfile(id)` updates all queries immediately
5. Toast: "◆ SWITCHED — Now in [Profile Name]"
6. Omnibar closes

**Command list (empty input):**
1. `Cmd+K` without typing → shows all available commands
2. `/ingest [text]` — Quick text capture (0 credits)
3. `/profile` — Switch active profile
4. `/search [query]` — Search memories (shows "not yet implemented" — BUG-021)
5. `/generate [prompt]` — Generate Meta-Doc (shows "not yet implemented" — BUG-021)

---

## Subcomponents

```
components/domain/
  Omnibar.tsx           — Main Omnibar container with keyboard handler
  OmnibarInput.tsx      — Search input with slash command detection
  CommandList.tsx       — Command list when input is empty
  ProfileSwitchList.tsx — Profile list for /profile command
  IngestConfirm.tsx     — Inline preview before /ingest capture

hooks/
  use-omnibar.ts        — Cmd+K/Ctrl+K open/close, keyboard navigation

lib/
  omnibar-commands.ts   — Command definitions: /ingest, /profile
```

---

## API Contracts

```
POST /v1/ingest/text
  Request:  { content: string, profile_id?: string, tags?: string[] }
  Response: { job_id: string }
  Auth:     Required
  Cost:     0 credits (text ingest is always free)
  Limit:    50,000 chars max — show inline error if exceeded

GET /v1/profiles
  Response: { profiles: [{ id, name, is_default, icon, color }] }
  Auth:     Required
  Used by:  Populate /profile dropdown (fetched from ProfileContext, not directly)
```

---

## Admin Bypass

Text ingest: 0 credits — no bypass needed.
Profile switching: no cost — no bypass needed.
Omnibar is fully functional for all users without any special admin handling.

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)

Specific rules:
- **Omnibar container:** `bg-card rounded-2xl shadow-lg border border-border` — warm cream card, not modal overlay
- **Position:** Fixed, centered at top of viewport: `fixed top-4 left-1/2 -translate-x-1/2 z-50`
- **Width:** `w-full max-w-lg` (not full-width on desktop)
- **Input:** no ring, no border — seamless inside the Omnibar container
- **Command items:** hover state `bg-secondary`, active `bg-primary/10 text-primary`
- **Command prefix text:** `font-mono text-sm` for `/ingest`, `/profile` etc.
- **Toast confirmation:** `sonner` — `toast.success("◆ CAPTURED — Added to [Profile Name]")`
- **Active profile checkmark:** `text-primary` — `✓` or `CheckCircle2` icon
- **Max height:** `max-h-[400px] overflow-y-auto` for profile list

---

## Known Bugs / Current State

**BUG-021 (MEDIUM):** `/search` and `/generate` commands show "not yet implemented" toast without doing anything.
- **Root cause:** `components/domain/Omnibar.tsx:221-225` has placeholder handlers that call `toast.info("not yet implemented")`.
- **Fix:** Either implement the commands (link `/search` to search page, `/generate` to workstation with the query pre-filled) OR hide these commands from the command list entirely until implemented.
- **Recommended fix:** Remove `/search` and `/generate` from the CommandList until they're implemented. Showing unimplemented features creates user confusion.
- **Story:** STORY-041

**BUG-022 (MEDIUM — Memory Leak):** `ReadableStream.getReader()` in MemoryChat not cancelled on unmount.
- **Note:** This is in MemoryChat, not Omnibar — but related to SSE/stream cleanup. See FE-COMP-08 (MemoryChat).

---

## Acceptance Criteria

- [ ] `Cmd+K` opens Omnibar; `Escape` closes it
- [ ] Empty input → shows command list (`/ingest`, `/profile`)
- [ ] `/ingest Hello world` + Enter → `POST /v1/ingest/text` fires → toast "Captured to [Profile]"
- [ ] Text > 50,000 chars → inline error "Text exceeds 50,000 characters" (not a toast)
- [ ] `/profile` → shows all profiles, active one has `✓`
- [ ] Profile switch → all dashboard queries refetch with new `profile_id`
- [ ] After any command → Omnibar closes automatically
- [ ] Focus trapped inside Omnibar (Tab cycles through items)
- [ ] Mobile: header button opens Omnibar (no keyboard shortcut on mobile)
- [ ] Unimplemented commands (`/search`, `/generate`) either removed OR clearly marked

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `BE-COMP-01-IngestionPipeline.md` — text ingest endpoint details
- `docs/architecture/03-api-contract.md` — `/v1/ingest/text` endpoint
- `docs/components/REFACTOR_PLAN.md` — BUG-021 fix details

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-008](../stories/EPIC-02-ingestion/STORY-008.md) | Text Quick-Capture (Omnibar /ingest) | Frontend | `/ingest [text]` slash command |
| [STORY-020](../stories/EPIC-06-auth-profiles/STORY-020.md) | Profile Switching (Omnibar /profile) | Frontend | `/profile` command + active context |

---

## Component Files

```
components/domain/
  Omnibar.tsx           — Main Omnibar container with keyboard handler
  OmnibarInput.tsx      — Search input with slash command detection
  CommandList.tsx       — Command list when input is empty
  ProfileSwitchList.tsx — Profile list for /profile command

hooks/
  use-omnibar.ts        — Cmd+K/Ctrl+K open/close, keyboard navigation

lib/
  omnibar-commands.ts   — Command definitions
```

## Slash Command Detection

```tsx
const COMMANDS = ["/ingest", "/profile"] as const  // /search, /generate removed (BUG-021 fix)

function detectCommand(input: string): { command: string | null; args: string } {
  const trimmed = input.trim()
  for (const cmd of COMMANDS) {
    if (trimmed.startsWith(`${cmd} `) || trimmed === cmd) {
      return { command: cmd, args: trimmed.slice(cmd.length).trim() }
    }
  }
  return { command: null, args: "" }
}
```

## Omnibar Container Pattern

```tsx
// Omnibar.tsx
"use client"
import { useEffect, useState } from "react"
import { CommandDialog, CommandInput, CommandList, CommandItem } from "~/components/ui/command"
import { toast } from "sonner"
import { useProfileContext } from "~/contexts/profile-context"
import { useApiFetch } from "@/lib/api-client"

export function Omnibar() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const apiFetch = useApiFetch()
  const { profiles, activeProfile, switchProfile } = useProfileContext()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

  const handleSubmit = async () => {
    const { command, args } = detectCommand(input)
    if (command === "/ingest") {
      if (args.length > 50_000) { setError("Text exceeds 50,000 characters"); return }
      await apiFetch("/v1/ingest/text", {
        method: "POST",
        body: JSON.stringify({ content: args, profile_id: activeProfile?.id })
      })
      toast.success(`◆ CAPTURED — Added to ${activeProfile?.name ?? "Default"}`)
      setOpen(false)
      setInput("")
    }
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput value={input} onValueChange={setInput}
        placeholder="Type /ingest or /profile..." />
      <CommandList>
        {input === "" && (
          <>
            <CommandItem onSelect={() => setInput("/ingest ")}>
              <span className="font-mono text-sm">/ingest [text]</span>
              <span className="text-xs text-muted-foreground ml-2">Quick text capture</span>
            </CommandItem>
            <CommandItem onSelect={() => setInput("/profile ")}>
              <span className="font-mono text-sm">/profile</span>
              <span className="text-xs text-muted-foreground ml-2">Switch active profile</span>
            </CommandItem>
          </>
        )}
        {input.startsWith("/profile") && profiles.map(p => (
          <CommandItem key={p.id} onSelect={() => {
            switchProfile(p.id)
            toast.success(`◆ SWITCHED — Now in ${p.name}`)
            setOpen(false)
          }}>
            {p.name}
            {p.id === activeProfile?.id && <span className="ml-auto text-primary">✓</span>}
          </CommandItem>
        ))}
      </CommandList>
    </CommandDialog>
  )
}
```

## Profile Context Pattern

```tsx
// contexts/profile-context.tsx
export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null)
  const apiFetch = useApiFetch()
  const queryClient = useQueryClient()

  const { data: profiles } = useQuery({
    queryKey: ["profiles"],
    queryFn: () => apiFetch<{ profiles: Profile[] }>("/v1/profiles"),
  })

  const activeProfile = profiles?.profiles.find(p => p.id === activeProfileId)
    ?? profiles?.profiles.find(p => p.is_default)
    ?? null

  const switchProfile = (id: string) => {
    setActiveProfileId(id)
    queryClient.invalidateQueries({ queryKey: ["sources"] })
    queryClient.invalidateQueries({ queryKey: ["graph"] })
    queryClient.invalidateQueries({ queryKey: ["metadocs"] })
  }

  return (
    <ProfileContext.Provider value={{ profiles: profiles?.profiles ?? [], activeProfile, switchProfile }}>
      {children}
    </ProfileContext.Provider>
  )
}
```
