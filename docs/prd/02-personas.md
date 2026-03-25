# PRD — 02. Target Personas

> **Cross-references:** `prd/03-feature-specs/` (features mapped to personas) | `design/03-screen-flows.md`

---

## Persona 1: The Technical Power User

**Name:** Aria, 28 — Senior Software Engineer at a fintech startup
**Location:** Singapore | **Tier target:** Pro ($15/mo)

### Jobs-to-be-Done
- **Functional:** "Help me recall all the architecture decisions I've made in the last 2 years without re-reading 50 Notion pages"
- **Emotional:** "Make me feel like I have complete command of my professional knowledge"
- **Social:** "Help me look consistently authoritative in cross-team technical discussions"

### Current Behavior
- Uses Claude ~6 hours/day across 3-4 different projects
- Has 3 years of chat logs (ChatGPT, Claude), ~300 notes in Obsidian
- Writes architecture docs weekly; re-explains context every time she starts a new AI session
- Explicitly frustrated by Claude's project silos — cannot cross-reference "What patterns did I use in Project X that would apply to Project Y?"

### Pain Points
- Spends ~2 hours/week re-explaining context to AI
- Has made architectural mistakes because the AI didn't know a past decision
- Cannot find "that conversation where I figured out the DB sharding approach 8 months ago"

### Ravenbase Use Cases
1. Upload all Obsidian notes + ChatGPT exports on day 1
2. Create System Profile "Work — Fintech Backend"
3. Daily: paste quick decisions into Omnibar for immediate capture
4. Weekly: ask "What architecture decisions have I made about service boundaries in the last 6 months?" → structured summary
5. Quarterly: "Generate my technical portfolio for performance review" → Meta-Document

### Success Signal
> *"It remembered I chose Postgres over MySQL in 2023 and explained exactly why — I had totally forgotten that conversation."*

---

## Persona 2: The Graduate Student / Researcher

**Name:** Jedi, 22 — Data Science student, juggling 5 coursework projects simultaneously
**Location:** Bangkok, Thailand | **Tier target:** Free → Pro after proof of value

### Jobs-to-be-Done
- **Functional:** "Synthesize 3 years of coursework, projects, and internship into my internship report without 2 weeks of manual work"
- **Emotional:** "Feel like my learning is accumulating into something coherent rather than scattered noise"
- **Social:** "Present myself as a thoughtful, connected practitioner in interviews and presentations"

### Current Behavior
- Uses Claude and ChatGPT heavily for homework, projects, research
- Has ~200+ Apple Notes (imported to Obsidian), class project files, multiple internship documents
- Switches between contexts constantly (ML assignment → database project → AI trainer work)
- Has never successfully synthesized his entire learning history into a single document

### Pain Points
- Internship report writing is a nightmare — manually extracting relevant content from 200+ notes
- AI assistants don't know his academic background when helping with new projects
- Frequently re-explains who he is, what he's studying, what tools he prefers

### Ravenbase Use Cases
1. Ingest entire Obsidian vault ZIP + coursework PDFs
2. System Profiles: "Academic — Data Science", "Work — AI Trainer", "Personal"
3. Meta-Document: "Generate my 3-year learning narrative for the Data Science internship report"
4. Query: "What ML techniques have I worked with, organized by project timeline?"
5. Memory Inbox: resolve conflict when "studying React" appears alongside "using Vue for all projects"

### Success Signal
> *"It found a project I had completely forgotten about from my second year and included it in exactly the right context."*

---

## Persona 3: The Creative Knowledge Worker

**Name:** Maria, 35 — UX Designer and independent consultant, managing 6+ client brands
**Location:** Barcelona, Spain | **Tier target:** Pro

### Jobs-to-be-Done
- **Functional:** "Know everything about Client X without re-reading 60 Slack messages every meeting"
- **Emotional:** "Feel like a trusted expert who has total recall of every client's history"
- **Social:** "Impress clients with continuity and institutional memory that makes me irreplaceable"

### Current Behavior
- Works with 6+ clients simultaneously; each has different brand guidelines, preferences, decision history
- Uses Notion for client management but AI chat history is siloed
- Frequently frustrated by AI assistants that don't know which client she's currently discussing
- Uploads client briefs, AI-generated copy, meeting transcripts to various tools — never unified

### Ravenbase Use Cases
1. System Profile per client: "Client — RunaKhao Brand", "Client — TechStartup"
2. Upload all client documents, transcripts, previous AI conversation exports
3. Memory Inbox: when client changes brand voice, resolve "formal tone" vs "conversational tone" conflict
4. Meta-Document: "Summarize all design decisions for Client X across our entire engagement"
5. Omnibar: capture quick insights during client calls immediately

### Success Signal
> *"It knew we'd decided on that specific shade of green for the brand 8 months ago and why — without me searching for the email."*

---

## Persona Comparison Table

| Attribute | Aria (Engineer) | Jedi (Student) | Maria (Consultant) |
|---|---|---|---|
| AI usage | 6h/day professional | 4h/day mixed | 3h/day client-focused |
| Data volume | High (3yr chat + notes) | Medium (200+ notes + docs) | Medium (per-client docs) |
| Key feature | Cross-project synthesis | Internship report generation | Client profile isolation |
| Context switching | Between projects | Between courses/projects | Between clients |
| Primary concern | Technical accuracy | Completeness | Confidentiality |
| WTP | $15/mo | $0-$10/mo | $15/mo |
