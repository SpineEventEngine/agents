---
description: Resolve a Maven artifact's on-disk sources instead of unzipping Gradle-cache JARs.
argument-hint: "<group:artifact[:version] | artifact>"
allowed-tools: Read, Grep, Glob, Write, Bash(.agents/scripts/api-discovery/discover:*), Bash(.agents/scripts/api-discovery/update-sibling:*), Bash(mkdir:*)
model: haiku
---

Follow the `api-discovery` skill exactly:

- Skill: `.agents/skills/api-discovery/SKILL.md`
- Query: $ARGUMENTS
- Run `.agents/scripts/api-discovery/discover $ARGUMENTS`; stdout is the
  resolved path, stderr carries warnings the user must see.
- Exit 10 → run the skill's bootstrap flow (ask the user before creating
  the cache directory). Exit 1 → report the failure verbatim; never fall
  back to `unzip` against Gradle caches.
- On a `STALE:` warning, offer `update-sibling` per the skill and read its
  stdout token (`pulled` | `up-to-date` | `skipped-branch`) to decide the
  next step.
- Report the resolved path and any warnings so follow-up work can read the
  sources directly.
