# Design — 00. Brand Identity

> **Cross-references:** `design/01-design-system.md` (tokens) | `design/03-screen-flows.md` (applications)

---

## Brand Essence

**One-sentence brand:** Ravenbase is the AI memory layer that treats your knowledge as
permanent, structured, and yours — the way a raven remembers every detail of every encounter.

**Name origin:** Ravens possess highly developed episodic-like memory, allowing them to
remember specific past events — what happened, where, and when — and use this information
to navigate complex social situations and plan for the future. Ravenbase brings this same
quality of permanent, structured, contextual memory to human-AI interaction.

**Brand archetype:** The Intelligent Witness — precise, observant, permanently attentive,
and absolutely trustworthy with what it has seen.

**Personality axes:**
- Intelligent ←→ Approachable (65% intelligent, 35% approachable)
- Precise ←→ Expressive (70% precise, 30% expressive)
- Warm / Grounded ←→ Minimal (60% warm/grounded, 40% minimal — aged paper meets clean UX)

---

## Voice & Tone

### Principles
- **Precise over flowery** — "Your knowledge graph has 247 nodes" not "Your amazing knowledge web is growing!"
- **Active over passive** — "Detected a conflict" not "A conflict was detected"
- **Technical terms are OK** — Our users understand "vector search", "knowledge graph", "semantic similarity"
- **Human over corporate** — Never say "leverage", "utilize", "synergy"
- **Direct over hedged** — "This conflicts with what you said in 2022" not "This may potentially conflict..."

### Do / Don't Examples

| Context | ✅ Do | ❌ Don't |
|---|---|---|
| Empty state | "Upload your first file to start building your knowledge graph" | "Get started on your amazing knowledge journey!" |
| Conflict detected | "React vs Vue: one of these isn't current anymore" | "We've detected a potential inconsistency!" |
| Meta-Doc generating | "Synthesizing your last 3 years..." | "Our AI is working hard to craft your document!" |
| Error message | "Upload failed: file exceeds 50MB limit" | "Oops! Something went wrong 😅" |
| Success | "Indexed 42 chunks across 3 concepts" | "Woohoo! Your file is ready!" |

### Mono Label Pattern (Critical Brand Element)

The `◆ MONO_LABEL` pattern from the UI template is a central brand expression. Labels read like system identifiers — technical, precise, and deliberately machine-aesthetic:

```
◆ KNOWLEDGE_GRAPH       (section identifier)
◆ SYSTEM_MODULES        (features section)
◆ HALL_OF_RECORDS       (testimonials)
◆ CONFLICT_QUEUE        (Memory Inbox badge)
◆ KNOWLEDGE_INDEX       (source list)
REF-0042               (reference IDs)
MEM-0088               (memory node IDs)
SRC-0007               (source IDs)
RESOLVED               (status chips)
PENDING                (status chips)
ALL_SYSTEMS_OPERATIONAL (footer status)
```

---

## Logo & Wordmark

The Ravenbase logo is a custom SVG mark. It is the only permitted brand mark.
The placeholder `R` letterform used previously is retired.

### The SVG Mark

```tsx
// The canonical logo SVG — use via the <RavenbaseLogo> component, never inline
// Source SVG viewBox: 0 0 64 42 (width=64, height=42 natural proportions)

const RAVENBASE_SVG_PATH = `M19.6223 0.0276122C22.1412 -0.0148667 24.6972 0.0143591 27.2164 0.0250993C28.8906 0.032225 31.0884 -0.0956587 32.712 0.165686C36.369 0.754264 39.7525 3.04265 41.6732 6.19766C42.2315 7.11484 42.6877 8.19041 43.0525 9.20581L49.0961 9.20626C53.2355 9.23204 56.7525 10.6451 59.6439 13.6117C62.0057 16.0348 63.5323 19.3277 63.8916 22.6894C64.0278 23.9613 64.0009 25.4034 63.9912 26.6905L45.7985 26.6936C44.3846 26.6942 42.9081 26.6268 41.5253 26.9473C39.0794 27.5139 37.1269 29.0206 35.8069 31.1211C34.9196 32.5556 34.4062 34.189 34.3137 35.8723C34.2786 36.4482 34.3089 37.0816 34.2982 37.6627C34.2724 39.0775 34.3403 40.5763 34.2689 41.9839C33.0672 41.9708 31.8578 41.9942 30.6562 41.9818C29.5226 41.9705 28.5579 42.0624 27.4497 41.788C26.0476 41.441 24.9227 40.9942 23.7256 40.1763C22.6845 39.4651 21.9897 38.7054 21.1213 37.8155C20.1728 36.8441 19.2418 35.8551 18.3012 34.8764C17.8327 34.3859 17.3608 33.8984 16.8858 33.4141C16.1687 32.6881 15.2523 31.7845 14.7201 30.9215C13.7392 29.3314 13.3418 27.3004 13.8066 25.4743C14.1449 24.276 14.9999 22.5307 16.1016 21.8739C17.2714 21.1768 18.6864 21.6873 19.3423 22.8367C19.7869 23.6278 19.7741 24.5958 19.3088 25.3748C19.044 25.8133 18.6816 26.2027 18.5526 26.7101C18.3774 27.4041 18.72 28.0987 19.1746 28.6024C20.1063 29.6344 21.1084 30.5879 22.0768 31.5821L24.7844 34.3756C25.9867 35.6045 26.6689 36.4785 28.433 36.8465C28.7506 36.914 29.0745 36.9474 29.3992 36.946C29.4023 35.9993 29.4479 34.7425 29.6137 33.8076C29.9506 31.9081 30.8111 29.5714 32.0085 28.0492C32.0451 28.045 32.0816 28.0406 32.1182 28.0354C32.9554 27.9242 34.2837 27.5039 35.0734 27.192C38.1331 25.9837 40.2208 24.2237 42.1922 21.6677L58.717 21.6646C58.6039 21.319 58.4863 20.9696 58.3563 20.6315C57.1777 17.5635 54.5473 15.1437 51.2948 14.467C50.1051 14.2194 49.1468 14.2643 47.9361 14.2646L34.3199 14.266C33.873 14.2666 33.3844 14.2859 32.9444 14.2674C32.763 14.5252 32.5689 14.8213 32.353 15.0492C30.9652 16.5154 28.8034 16.5797 27.3348 15.1585C26.6889 14.5303 26.324 13.6687 26.3225 12.7686C26.3123 11.7227 26.6423 10.9572 27.3654 10.216C28.1196 9.44271 28.947 9.20092 30.0032 9.20488C30.773 9.20777 31.5371 9.20388 32.3006 9.20416L37.6838 9.20381C37.4166 8.79283 37.0293 8.18525 36.7079 7.82115C35.2989 6.19779 33.2961 5.20729 31.1489 5.07203C30.3429 5.02343 29.4724 5.05079 28.6605 5.05558L25.2249 5.06353L21.8003 5.05833C20.3926 5.05172 19.0506 4.97365 17.6785 5.32729C16.2553 5.69407 14.8565 6.42406 13.762 7.40084C12.0798 8.90877 10.9859 10.962 10.6739 13.1975C10.5939 13.7453 10.5722 14.5747 10.5384 15.15C10.2603 15.4404 9.91758 15.7208 9.62926 16.013C8.55948 17.0973 7.4646 18.2383 6.37858 19.3002C5.59832 16.7814 5.40131 14.5931 5.88201 11.9758C7.10921 5.29424 12.7075 0.245962 19.6223 0.0276122Z M18.3332 37.0334C16.4383 39.0837 14.8786 40.7608 12.1265 41.608C6.46503 43.3505 0.685733 39.0513 0.0694719 33.3139C-0.24899 30.6013 0.535971 27.8746 2.24849 25.7445C2.78333 25.0815 3.45376 24.4185 4.05532 23.804L6.44151 21.3741C7.47591 20.3169 8.51624 19.2654 9.5625 18.2198C10.7424 17.0409 11.7453 15.9015 13.3052 15.2169C14.369 14.75 15.308 14.4555 16.4728 14.3353C18.8583 14.1046 21.2372 14.8352 23.0803 16.3644C25.1217 18.0488 26.42 20.4649 26.6965 23.0946C26.5835 23.4663 26.6298 24.8887 26.6877 25.2959C26.6907 25.5882 26.5822 26.1077 26.5156 26.4102C26.0853 28.3662 25.173 29.7301 23.9331 31.2447C23.5798 30.9728 22.6438 29.969 22.2938 29.6147C21.7273 29.0419 20.9848 28.3208 20.4611 27.7256C21.6475 26.4078 22.0355 24.8226 21.7266 23.0887C21.2692 20.5217 18.6679 18.7272 16.1098 19.4626C15.1783 19.7304 14.5365 20.1015 13.8574 20.8033C12.5754 22.1066 11.3086 23.4285 10.0178 24.7231C9.19781 25.5417 8.38548 26.3676 7.58091 27.2013C7.06383 27.7294 6.47978 28.2698 6.02933 28.8471C4.36115 30.9852 4.58085 33.8231 6.46309 35.7053C7.2889 36.515 8.403 36.9642 9.56043 36.9539C12.0772 36.9353 13.2671 35.1511 14.8981 33.5036L18.3332 37.0334Z M38.2483 15.7588C38.4914 15.7517 38.7418 15.7531 38.9845 15.7571C40.3949 15.7801 41.8129 15.7366 43.2215 15.7731C42.8946 17.1218 42.496 18.2683 41.8015 19.479C40.1397 22.4422 37.4762 24.7187 34.2875 25.9015C33.6903 26.1228 33.0313 26.2901 32.4134 26.4577C30.903 26.7662 29.6156 26.7214 28.083 26.6932C28.3798 25.3335 28.3904 22.9995 28.0175 21.6673C29.5081 21.6787 30.9937 21.7672 32.423 21.289C34.6793 20.5334 36.3362 19.1545 37.5179 17.1296C37.6793 16.8518 37.8228 16.564 37.9473 16.2679C38.0276 16.0724 38.0445 15.8204 38.2483 15.7588Z M26.6965 23.0946C26.5835 23.4663 26.6298 24.8887 26.6877 25.2959C26.7559 24.9493 26.7301 23.4615 26.6965 23.0946Z`
```

### Logo Component Specification

The logo renders as a single SVG with a `fill` prop for color control.
The natural SVG is **64×42px**. All size variants scale proportionally.

```tsx
// components/brand/RavenbaseLogo.tsx
interface RavenbaseLogoProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl"
  color?: string   // CSS color value, defaults to "currentColor"
  className?: string
}

// Size scale — width×height, maintaining 64:42 ratio (≈1.524:1)
const SIZES = {
  xs:  { width: 24,  height: 16  },   // micro — favicon, tiny badges
  sm:  { width: 32,  height: 21  },   // small — sidebar icon-only mode
  md:  { width: 48,  height: 31  },   // medium — sidebar header, onboarding
  lg:  { width: 64,  height: 42  },   // large — landing hero, auth pages (base size)
  xl:  { width: 96,  height: 63  },   // xl — marketing hero, OG image
}
```

### Lockup Specification (Logo + Wordmark)

The lockup pairs the SVG mark with "RAVENBASE" in DM Sans Bold, all caps.
Gap between mark and type is always `8px`. Color is always the same for both elements.

```tsx
// components/brand/RavenbaseLockup.tsx
// Logo on left, type on right, 8px gap, same color for both

// Type size paired to logo size:
// xs  (24×16)  → text-sm  (14px) — not recommended, use mark alone
// sm  (32×21)  → text-base (16px)
// md  (48×31)  → text-xl   (20px)
// lg  (64×42)  → text-3xl  (30px) — primary lockup
// xl  (96×63)  → text-4xl  (36px) — hero usage only

// Wordmark: DM Sans, 800 weight (ExtraBold), tracking-wider, all caps
// "RAVENBASE" — no period, no tagline, no descriptor in the lockup

<div className="flex items-center gap-2">
  <RavenbaseLogo size="lg" color="currentColor" />
  <span
    className="font-sans font-extrabold tracking-wider uppercase"
    style={{ fontSize: "30px", lineHeight: 1 }}
  >
    RAVENBASE
  </span>
</div>
```

### Color Usage Rules

| Context | Logo color | Wordmark color |
|---|---|---|
| Light background | `text-primary` (`#2d4a3e`) | `text-primary` |
| Dark background / sidebar | `text-primary-foreground` (white) | `text-primary-foreground` |
| Monochrome print | `#000000` | `#000000` |
| Reverse (on primary bg) | `text-primary-foreground` | `text-primary-foreground` |

**Never:** Use the logo in muted colors, opacity < 100%, or in gradients.
**Never:** Use the lockup with the period (that's the Wordmark-only variant).
**Never:** Stretch, rotate, or recolor mark and type differently from each other.

### Where Each Variant Is Used

| Variant | Used in |
|---|---|
| Lockup `lg` (64px logo) | Landing page header, auth pages, onboarding |
| Lockup `md` (48px logo) | Dashboard sidebar header (visible state) |
| Mark-only `sm` (32px) | Dashboard sidebar icon-only / collapsed state |
| Mark-only `xs` (24px) | Browser favicon, mobile top bar |
| Lockup `xl` (96px logo) | Marketing hero section, OG social image |

### Files to Create (STORY-018-FE or STORY-001-WEB — whichever creates the first header)

```
components/brand/RavenbaseLogo.tsx   ← SVG mark component with size prop
components/brand/RavenbaseLockup.tsx ← Mark + type lockup component
components/brand/index.ts            ← re-exports both
```

These components replace every instance of the old `<div>` placeholder with `R` inside.

---

## Color Philosophy

**Primary:** Deep forest green (`#2d4a3e`) — knowledge, permanence, nature, memory.
Not blue-tech. Not black-minimal. Green as in growth, as in permanence, as in a raven's forest home.

**Background:** Warm cream (`#f5f3ee`) — aged paper, library, long-form reading.
The product feels like a thoughtful tool, not a dashboard.

**Surface:** Clean white (`#ffffff`) cards on cream background — elevated, clear, legible.

**Default mode:** Light. The product invites you in with warmth.
Dark mode is available for late-night sessions via the mode toggle.

---

## Photography & Illustration Direction

**The Aesthetic:** Warm, grounded, intelligent.
Think: a well-stocked academic library with shafts of light through tall windows.
Not a server room. Not a night-mode dashboard. Not a tech startup's RGB-lit office.

**Background palette:** Warm creams, aged paper tones, botanical greens.
**Accent energy:** Forest green for primary actions, amber/yellow for attention states.

**Avoid:**
- Generic stock photos of people at computers
- Abstract "AI brain" blue-glowing orb imagery
- Cute bird photography (too literal — the raven is a metaphor, not a mascot)
- Cold blue-white "tech" colour palettes
- Dark-by-default UIs (dark mode is supported, not primary)
- Neon glow effects, RGB lighting aesthetics
- The generic "AI = glowing blue network" visual

**Use instead:**
- Natural textures — paper, bark, moss, ink
- Warm amber for attention (conflicts = amber, not red)
- Graph structures as art — node diagrams in forest greens
- Botanical/organic shapes alongside precise technical elements
- High-contrast architectural photography (libraries, archives, observatories)
- Topographic maps, annotated diagrams, handwritten-note textures

---

## Mono Label Pattern (Core Brand Expression)

```tsx
// Standard pattern — underscore-separated, all caps, muted
<span className="text-xs font-mono text-muted-foreground tracking-wider">
  ◆ MEMORY_INBOX
</span>

// Numbered section labels (in pages and marketing)
<span className="text-xs font-mono text-muted-foreground tracking-wider">
  01 — BRAND_IDENTITY
</span>
```

Examples in use:
- `◆ RAVENBASE` — brand mark
- `◆ EPISODIC_MEMORY_LAYER` — product descriptor
- `◆ MEMORY_CONFLICT` — conflict card header
- `◆ AI_SUGGESTION` — AI reasoning panel
- `◆ KNOWLEDGE_GRAPH` — graph explorer header
- `◆ LIVE_PREVIEW` — workstation streaming preview
- `◆ ALL_SYSTEMS_OPERATIONAL` — footer status bar
- `REF-0088` — testimonial reference IDs

---

## Product Screenshots / Demo Aesthetic

Dashboard screenshots should always show:
- Light mode default (warm cream background, forest green sidebar)
- Real-looking (but fake) data — named concepts like "TypeScript", "System Design", "Internship 2023"
- The mono label system visible
- The sidebar with profile indicator showing (green sidebar, white text)

Landing page mockups should be clean, warm, and suggest depth — a graph with 40+ nodes is more impressive than an empty graph.
