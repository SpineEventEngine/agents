---
description: >
  Check the Hugo documentation site for broken links, mirroring CI's
  Check Links job.
argument-hint: "[base-ref]"
allowed-tools: Read, Grep, Glob, Bash
model: haiku
---

Follow the `check-links` skill exactly:

- Skill: `.agents/skills/check-links/SKILL.md`
- Base ref for the scope check: $ARGUMENTS (treat empty as `master`).
- The skill owns the procedure (site detection, binary preflight against
  the CI-pinned versions, `npm ci`, Hugo build and serve on port `1414`,
  the Lychee run, teardown) and the report format (broken URLs grouped by
  source Markdown page).
- If no Hugo config exists under `docs/` or `site/`, return
  `APPROVE — no Hugo documentation site found under docs/ or site/.` and
  stop — do not write a `FAIL` sentinel for that case.
- When the pipeline runs, always tear the Hugo server down (step 8), even
  when Lychee fails, and write the `check-links.ok` sentinel to the
  repository's git directory.
