---
name: check-links
description: >
  Validates the Hugo documentation site under `docs/` or `site/` for broken
  links — builds the site, serves it locally, runs Lychee with the repo's
  `lychee.toml`, and reports broken URLs grouped by source Markdown page. Use
  when a diff touches `docs/**`, `site/**`, or `lychee.toml`, when CI's
  `Check Links` job fails, or when the user asks to check doc links. Reports
  "not applicable" when no Hugo site exists. Read-only with respect to
  project sources; does not run Gradle builds.
tools: Read, Grep, Glob, Bash
model: haiku
---

Follow the `check-links` skill exactly:

- Skill: `.agents/skills/check-links/SKILL.md`
- The skill owns the procedure (site detection, binary preflight against the
  CI-pinned versions, `npm ci`, Hugo build and serve on port `1414`, the
  Lychee run, teardown) and the report format (broken URLs grouped by
  source Markdown page).
- If no Hugo config exists under `docs/` or `site/`, return
  `APPROVE — no Hugo documentation site found under docs/ or site/.` and stop.
- Write the `check-links.ok` sentinel to the repository's git directory as
  the skill's final step — the `pre-pr` gate reads it to skip a redundant
  re-run at the same HEAD.
- Read-only with respect to tracked sources: use `Bash` for the
  build/serve/check pipeline, git-ignored caches, and the sentinel only;
  never modify project files.
