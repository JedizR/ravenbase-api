# Feature Spec — F7: System Profiles

> **Stories:** STORY-019, STORY-020
> **Cross-references:** `architecture/02-database-schema.md` (SystemProfile schema)

## Overview
Named context scopes that isolate AI queries. Switching profiles immediately changes the retrieval scope for all searches, conflict detection, and Meta-Document generation.

## Profile Properties
| Property | Type | Description |
|---|---|---|
| `name` | string | "Work — Full Stack", "Academic", "Personal" |
| `description` | string (optional) | Brief description |
| `icon` | emoji | Visual identifier in sidebar |
| `color` | hex | Badge color in sidebar |
| `is_default` | boolean | Active on login |

## Behavior Rules
- **Profile-scoped retrieval:** Qdrant and Neo4j queries filter by `profile_id` when profile is active
- **Cross-profile query:** Toggle in search/generation unlocks all profiles for one query
- **Default profile:** Created during onboarding. Cannot be deleted.
- **Switching:** Pure client-side React context update — no API call (< 50ms)
- **Ingestion assignment:** Files uploaded while a profile is active are tagged with that `profile_id`

## Acceptance Criteria
- [ ] CRUD for profiles in Settings → Profiles
- [ ] Active profile shown in sidebar with icon + color badge
- [ ] Profile switch via sidebar dropdown AND `/profile` Omnibar command
- [ ] All search/graph/generation requests include active `profile_id`
- [ ] Cross-profile toggle works in both search and Workstation
- [ ] Deleting a profile: requires reassigning its memories to another profile first
- [ ] Default profile cannot be deleted (validation error with clear message)
