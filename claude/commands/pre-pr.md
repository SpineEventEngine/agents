---
description: >
  Run the applicable pre-PR checklist (version gate, build/check,
  reviewers) and write a sentinel so `gh pr create` is unblocked.
argument-hint: "[base-ref]"
allowed-tools: Read, Write, Grep, Glob, Agent, Bash
---

Follow the `pre-pr` skill exactly:

- Skill: `.agents/skills/pre-pr/SKILL.md`
- Base ref: $ARGUMENTS (treat empty as `master`).
- Detect whether the repository-root `version.gradle.kts` exists. If it is
  absent at both the base ref and `HEAD`, the version check is `N/A`; do not
  create the file and do not ask for `/bump-version`.
- Run the build/check command selected by the skill and
  `.agents/guidelines/running-builds.md`. The command may be Gradle or non-Gradle.
- Dispatch the reviewers as Claude subagents in parallel — send a single
  message with multiple Agent tool uses:
  - `kotlin-engineer` when `.kt|.kts` files changed (general Kotlin language
    standards).
  - `spine-code-review` when `.kt|.kts|.java` files changed, or when build-only
    files changed (`*.gradle`, `settings.gradle`, `gradle.properties`,
    `*.versions.toml`) — its scope includes build changes (repo-specific
    rules). When `.kt|.kts` changed it runs alongside `kotlin-engineer`
    (disjoint concerns, no double-reporting); a Java-only or build-only diff
    dispatches `spine-code-review` alone (`kotlin-engineer` is Kotlin-only).
  - `review-docs` when `.md` files or KDoc inside sources changed.
  - `dependency-audit` when any file under
    `buildSrc/src/main/kotlin/io/spine/dependency/` changed.
  - `check-links` when a Hugo site exists (a Hugo config under `docs/` or
    `site/`) and the diff touches files under the site directory or
    `lychee.toml`. Honor the `check-links.ok` sentinel short-circuit from
    the skill: skip the dispatch when the sentinel matches the current
    HEAD with `status=PASS`.
- Pass the version-check status to reviewers. If it is `N/A`, tell them:
  "This repository has no root `version.gradle.kts`; a version bump is not
  applicable and must not be reported as missing."
- Each reviewer is read-only; do not pass it edit tools.
- On any reviewer returning `REQUEST CHANGES`, treat the overall result
  as `FAIL` and stop before writing the sentinel as `PASS`.
- Sentinel location: `$(git rev-parse --absolute-git-dir)/pre-pr.ok` — the
  resolved git directory (matching the hook), so it works in linked worktrees too
  (where `.git` is a file),
  format per the skill (`head=`, `branch=`, `status=`, `timestamp=`,
  `build=`, `reviewers=`, `version=`). Use `git rev-parse HEAD` for the
  SHA and `date -u +%Y-%m-%dT%H:%M:%SZ` for the timestamp.
- Do NOT run `gh pr create`. That is the user's next step.
