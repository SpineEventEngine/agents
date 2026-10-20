---
description: >
  Refresh external dependency versions in buildSrc to their latest
  non-snapshot release.
argument-hint: "[--dry-run] [paths...]"
allowed-tools: >-
  Read, Edit, Write, Grep, Glob, WebFetch, Bash(git status:*),
  Bash(git diff:*), Bash(./gradlew build:*), Bash(./gradlew clean build:*)
model: sonnet
---

Follow the `dependency-update` skill exactly:

- Skill: `.agents/skills/dependency-update/SKILL.md`
- Scope / flags: $ARGUMENTS
- Walk every dependency object under `buildSrc/src/main/kotlin/io/spine/dependency/`.
- Source of truth per artifact: the URL in the file's comment (line
  `// https://...` or KDoc `@see`). If no URL, fall back to Maven Central
  AND back-fill the URL comment.
- Filter out snapshots, RCs, alphas, betas, milestones, EAPs, and `-dev` builds.
- Apply the Kotlin version cap (`.agents/guidelines/kotlin-version-cap.md`): never
  raise Kotlin, or adopt a release that requires a newer Kotlin, above the Kotlin
  embedded in the Gradle version of `config`'s wrapper. Report held-back versions
  under "Capped" and values already above the cap under "Above the cap".
- Apply the edit. Do NOT commit; emit the report described in the skill.
- Flag `local/` (Spine SDK) updates separately so the user can decide whether to bump in lockstep.
- After the run, suggest the user review the diff and run `./gradlew build`
  (or `./gradlew clean build` if proto files participate). For `local/`
  bumps, suggest `./gradlew buildDependants`.
