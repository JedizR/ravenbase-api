# Feature Spec — F6: Omnibar

> **Stories:** STORY-008, STORY-020
> **Cross-references:** `design/02-component-library.md` | `design/04-ux-patterns.md`

## Overview
A persistent command-palette interface combining natural language chat, quick-capture, and slash-command access to all features. Mobile: fixed to bottom. Desktop: embedded in dashboard layout.

## Slash Commands

| Command | Syntax | Action |
|---|---|---|
| `/ingest` | `/ingest [text]` | Immediately ingests text as new memory |
| `/search` | `/search [query]` | Runs hybrid search, shows results panel |
| `/profile` | `/profile [name]` | Switches active System Profile |
| `/generate` | `/generate [prompt]` | Opens Workstation with prompt pre-filled |
| `/inbox` | `/inbox` | Navigates to Memory Inbox |
| `/graph` | `/graph` | Navigates to Graph Explorer |

## Visual Behavior
- Default state: placeholder `"/ Type to capture, search, or command..."` with `[⌘K]` hint
- On `/`: show slash-command autocomplete dropdown (cmdk-style)
- On text without slash: natural language mode (future: chat with context)
- Mobile: `position: fixed; bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)`

## Acceptance Criteria
- [ ] Global keyboard shortcut `/` focuses the Omnibar from anywhere in the dashboard
- [ ] Slash commands autocomplete on first character match
- [ ] `/ingest [text]` + Enter → confirmation toast "✓ Captured to [Profile]" within 2s
- [ ] `/profile [name]` → instant profile switch (< 50ms)
- [ ] Mobile: Omnibar fixed to bottom with safe area inset
