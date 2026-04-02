# Design — 03. Screen Flows & Page Layouts

> **Cross-references:** `design/02-component-library.md` | `stories/epics.md`

---

## Route Map

```
/ (root)
├── (marketing)/
│   ├── page.tsx               → Landing page
│   └── pricing/page.tsx       → Pricing page
│
├── (auth)/
│   ├── login/page.tsx         → Clerk SignIn
│   ├── register/page.tsx      → Clerk SignUp
│   └── onboarding/page.tsx    → 3-step wizard
│
└── (dashboard)/               ← Requires auth, light by default (dark if user toggled)
    ├── page.tsx               → Redirect to /graph
    ├── graph/page.tsx         → Graph Explorer
    ├── inbox/page.tsx         → Memory Inbox
    ├── workstation/page.tsx   → Meta-Document generator
    ├── sources/page.tsx       → Ingested files list
    └── settings/
        ├── page.tsx           → General settings
        ├── profiles/page.tsx  → System Profile CRUD
        └── billing/page.tsx   → Credits + Stripe portal
```

---

## Landing Page Layout

```
Background: #f5f3ee (warm cream) — the default page background
Header: sticky, bg-background/95 backdrop-blur, border-b border-border
CTA button style: bg-primary text-primary-foreground rounded-full (pill shape, forest green)

┌─────────────────────────────────────────────────────────────────┐
│  HEADER (sticky, blur, bg-background/95)                        │
│  [R] Ravenbase.    Product  Pricing  Sign In    [Get Started]   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  HERO SECTION                                                   │
│                                                                 │
│  ◆ EPISODIC_MEMORY_LAYER                                        │
│                                                                 │
│  Never repeat yourself          [animated knowledge graph       │
│  to AI again.                    mockup — force-directed,       │
│                                  ~40 nodes, dark/light blend]   │
│  [Years of scattered notes →                                    │
│   one structured memory]                                        │
│                                                                 │
│  [Start for free →]  [Watch demo]                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  HOW IT WORKS (◆ THE_PROTOCOL)                                  │
│  3 steps, horizontal on desktop, vertical on mobile:            │
│                                                                 │
│  [01 UPLOAD]      [02 STRUCTURE]     [03 GENERATE]              │
│  Drop your files  Graph builds       Ask for anything           │
│  notes, chats     automatically      Meta-Doc in 30s            │
│  PDFs, anything                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  FEATURES (◆ SYSTEM_MODULES)    [3-column grid]                 │
│                                                                 │
│  [Memory Inbox]    [Meta-Documents]  [Knowledge Graph]          │
│  Conflicts become  Years of context  Concepts connected         │
│  conversations,    → one perfect     across time, not           │
│  not silent        document          just semantics             │
│  overwrites                                                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  FEATURE DEEP-DIVE (alternating left/right sections)            │
│  Memory Inbox demo GIF    │ Explanatory copy                    │
│  ─────────────────────────┤───────────────────                  │
│  Explanatory copy         │ Meta-Doc demo GIF                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TESTIMONIALS (◆ HALL_OF_RECORDS)   [3-column cards]            │
│  REF-0088  "It remembered..."   REF-2301  "..."  REF-7725 "..." │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CTA SECTION (card with decorative corner icons)                │
│  "Your knowledge,              [corner icons: Upload, Graph,    │
│   structured forever."          Inbox, Doc]                     │
│  [Start for free →]                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  FOOTER                                                         │
│  [O] Ravenbase.    DIRECTORY    LEGAL    PROTOCOLS              │
│  MEMORY LAYER V1.0   Product_Tour Privacy  US-WEST-2 [ACTIVE]   │
│  ◆ ALL_SYSTEMS_OPERATIONAL                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dashboard Layout

```
Background: bg-background (cream by default, dark if .dark is toggled)
Sidebar: bg-primary (forest green) with primary-foreground text — this is always green

┌──────────────────────────────────────────────────────────────────┐
│ SIDEBAR (240px, bg-primary — forest green)    │  MAIN CONTENT    │
│ Text: primary-foreground (white/near-white)   │  (bg-background) │
│                                       │  (flex-1, bg-background) │
│ [R] Ravenbase  ▾ [Work Profile]       │                          │
│                                       │  HEADER BAR              │
│ ─────────────────────────             │  [Page title]  [search]  │
│ ◈  Graph Explorer                     │  [🌙 toggle] [notif] [av]│
│ ✉  Memory Inbox     [3]               │  ──────────────────────  │
│ ✦  Workstation                        │                          │
│ ◻  Sources (12)                       │  PAGE CONTENT            │
│                                       │                          │
│ ─────────────────────────             │                          │
│ ⚙  Settings                           │                          │
│ ◎  Credits: 1,847                     │                          │
│ ─────────────────────────             │                          │
│ [Profile name] [email]  [log out]     │                          │
└──────────────────────────────────────────────────────────────────┘

OMNIBAR (appears at bottom of main content area, desktop)
┌──────────────────────────────────────────────────────┐
│ ◆  /  Type to capture, search, or command...  [⌘K]   │
└──────────────────────────────────────────────────────┘
```

---

## Memory Inbox Page

```
ROUTE: /inbox

┌─────────────────────────────────────────────────────────────────┐
│  ◆ MEMORY_INBOX          [3 pending]   [filter: all profiles]   │
│                                                                 │
│  ← ACTIVE CONFLICT CARD (highlighted, border-primary) →         │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ◆ MEMORY_CONFLICT              [confidence: 94%] [SRC→]   │   │
│ │ ────────────────────────────────────────────────────────  │   │
│ │ OLD  "I use React for all frontend development"           │   │
│ │ NEW  "I now exclusively use Vue.js at work"               │   │
│ │ ────────────────────────────────────────────────────────  │   │
│ │ AI → Update primary stack to Vue. Tag React as Past.      │   │
│ │                                                           │   │
│ │ [↵ Enter: Accept]  [⌫ Keep Old]  [C: Discuss]  [? Help]   │   │
│ │ from: chat_2022.json  →  notes_march_2024.md              │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ← INACTIVE CARDS (opacity-60) →                                │
│  ┌────────────────────────────────┐ ┌───────────────────────┐   │
│  │ Python vs TypeScript conflict  │ │ Job title change      │   │
│  │ confidence: 87%                │ │ confidence: 91%       │   │
│  └────────────────────────────────┘ └───────────────────────┘   │
│                                                                 │
│  [J/K to navigate]                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workstation Page

```
ROUTE: /workstation

┌─────────────────────────────────────────────────────────────────┐
│  LEFT PANEL (documents history)   │  MAIN EDITOR                │
│  ───────────────────────────────  │  ────────────────────────   │
│  ◆ DOCUMENT_HISTORY               │  [toolbar: Export MD | PDF] │
│  ───────────────────────────────  │  [Sources (24)]  [Regen]    │
│  Resume — Next.js Role  [today]   │  ────────────────────────   │
│  Internship Report       [2d ago] │                             │
│  Project Portfolio       [1w ago] │  # Senior Full-Stack Eng... │
│                                   │                             │
│                                   │  ## Experience              │
│                                   │                             │
│                                   │  **Sense Info Tech** (2024) │
│                                   │  Built Thai government B2G  │
│                                   │  data pipelines using...    │
│                                   │  [streaming cursor ▌]       │
│                                   │                             │
│                                   │  ────────────────────────   │
│                                   │  ◆ GENERATE                 │
│                                   │  [Generate a 1-page resume  │
│                                   │   tailored for Next.js...]  │
│                                   │  [Sonnet ▾]  [→ Generate]   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Graph Explorer Page

```
ROUTE: /graph

┌─────────────────────────────────────────────────────────────────┐
│  FILTER BAR                                                     │
│  [Profile: Work ▾]  [Type: All ▾]  [Date: All time ▾]  [Reset]  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  GRAPH CANVAS (full width, full height)                         │
│                                                                 │
│    ○ TypeScript ─── ○ React ─ ─ ─ ○ Vue.js (amber, pulsing)     │
│         │                │                                      │
│    ○ Harbour.Space  ○ Project Atlas                             │
│         │                                                       │
│    □ resume_2023.pdf ─── □ notes_march_2024.md                  │
│                                                                 │
│  [NODE DETAIL PANEL — slides in from right on click]            │
│  ┌──────────────────────────────────────┐                       │
│  │ TypeScript                   ×       │                       │
│  │ type: SKILL | first: 2021            │                       │
│  │ ───────────────────────────────────  │                       │
│  │ ◆ LINKED_MEMORIES (12)               │                       │
│  │  "Used TS for internship project..." │                       │
│  │  "Prefers TS over JS for..."         │                       │
│  │ ───────────────────────────────────  │                       │
│  │ ◆ SOURCES (3)                        │                       │
│  │  resume_2023.pdf                     │                       │
│  │  chat_export_2024.json               │                       │
│  └──────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Onboarding Wizard

```
ROUTE: /onboarding

Step 1/3 — Create Your First Profile
┌────────────────────────────────────────────────────┐
│  What best describes you?                          │
│                                                    │
│  [◈ Software Engineer]  [◈ Student / Researcher]   │
│  [◈ Designer]           [◈ Consultant]             │
│  [◈ Other]                                         │
│                                                    │
│  Profile name: [Work — Software Engineer    ]      │
│                                                    │
│  [Continue →]                                      │
└────────────────────────────────────────────────────┘

Step 2/3 — Upload Your First File
┌────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────┐  │
│  │  Drop files here                             │  │
│  │  PDF, TXT, Markdown, ChatGPT export, Obsidian│  │
│  │  ZIP, or paste text below                    │  │
│  └──────────────────────────────────────────────┘  │
│  or                                                │
│  [Paste text from a note or conversation...]       │
│                                                    │
│  [Upload →]    [Skip for now]                      │
└────────────────────────────────────────────────────┘

Step 3/3 — Building Your Graph
┌────────────────────────────────────────────────────┐
│  ◆ PROCESSING_DOCUMENT                             │
│                                                    │
│  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  58%                        │
│  Extracting entities...                            │
│                                                    │
│  Found so far:                                     │
│  ○ TypeScript  ○ React  ○ Harbour.Space            │
│                                                    │
│  (auto-advances to dashboard when complete)        │
└────────────────────────────────────────────────────┘
```
