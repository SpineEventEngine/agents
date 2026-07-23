---
description: >
  Verify the branch bumped version.gradle.kts above base; recover via
  bump-version.
argument-hint: "[base-ref]"
allowed-tools: >-
  Read, Edit, Bash(.agents/skills/version-bumped/scripts/version-bumped.sh:*),
  Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(./gradlew:*)
model: haiku
---

Follow the `version-bumped` skill exactly:

- Skill: `.agents/skills/version-bumped/SKILL.md`
- Run the deterministic check
  `.agents/skills/version-bumped/scripts/version-bumped.sh`. If $ARGUMENTS
  names a base ref, run the script with `VERSION_BUMPED_BASE=<ref>`.
- Exit 0 → report the one-line confirmation and stop.
- Exit 2 → configuration error; surface the script's stderr and stop.
  Do not bump.
- Exit 1 → run the `bump-version` skill to recover (it owns the policy),
  then re-run the check once to confirm. Do not loop.
- Recovery may commit the bump — that is the `bump-version` skill's
  documented policy, a skill-declared `## Commit authorization`.
