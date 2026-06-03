---
slug: resolve-spine-task-group-link
branch: resolve-spine-task-group-link
owner: claude
status: draft
started: 2026-06-02
related-memories: []
---

## Goal

Resolve the dangling `spine-task-group-constant.md` reference in the
`gradle-review` skill so the "see …" pointer lands on a real, durable
target — by either **introducing** the shared `group = "spine"` task-group
constant and documenting it, or **delinking** until that constant exists.
Success: no reference in the repo points to a non-existent file, and the
`gradle-review` guidance still tells authors where the canonical value lives.

## Context

Codex flagged this on PR #4 (the link is *pre-existing* on `master`, not
introduced by that PR — `git blame` → `c9974788`). The guidance is a
forward-reference: "Every custom task must set `group`. The value must equal
`"spine"` (use the shared constant **once introduced** — see …)." The
referenced task plan was never created, so the link is broken.

Three live occurrences, all pointing at
`…/tasks/spine-task-group-constant.md` (a fourth, in `tasks.md`'s
"Spine-specific must-fix" section, was already delinked on this branch):

- `skills/gradle-review/SKILL.md:105`
  — href `../../tasks/spine-task-group-constant.md`
- `skills/gradle-review/spine-task-conventions.md:33`
  — href `../../tasks/spine-task-group-constant.md`
- `skills/gradle-review/practices/tasks.md:165` (Nits section)
  — href `../../../tasks/spine-task-group-constant.md`

Two problems, not one:

1. **The target file is missing** — nothing named `spine-task-group-constant.md`
   exists anywhere in the repo.
2. **The relative hrefs look wrong even if it existed** — they resolve to
   `<root>/tasks/…`, but task plans live under `.agents/tasks/…`. Whatever the
   final target is, the paths need re-checking against the `.agents/` symlink /
   submodule layout.

Note: pointing these references at a **task file** (`.agents/tasks/…`) is the
wrong durable target — task files are deleted on merge (see
`.agents/tasks/README.md` lifecycle). The reference should land on a lasting
home: a guideline, the constant's source, or its KDoc.

## Open decisions

- **Introduce vs. delink.** Create the shared constant (and a durable doc), or
  drop the parenthetical link until the constant exists?
- **Where the constant lives, if introduced.** Most likely the `config`
  repository's `buildSrc` (a Spine Gradle convention/plugin that sets
  `group = "spine"` on custom tasks), since `gradle-review`'s `buildSrc` scope
  is the `config` repo. Confirm the home before writing the reference.
- **Durable reference target.** A `guidelines/` page, the constant's source
  path, or the published KDoc — not a `.agents/tasks/` file.

## Plan

- [ ] Decide introduce vs. delink (see Open decisions).
- [ ] If delinking: keep the prose ("use the shared constant once introduced")
      but remove the hyperlink in all four spots.
- [ ] If introducing: define the `group = "spine"` constant in its agreed home,
      then point the four references at that durable target with correct
      relative paths (verified against the `.agents/` layout).
- [ ] Re-run a link check / grep to confirm no reference resolves to a missing
      file.

## Log

- 2026-06-02 — drafted as a follow-up from PR #4 review (Codex P2). The broken
  link is pre-existing on `master`; deferred out of PR #4's scope (line-length
  source-of-truth, guideline renames, task moves). Awaiting approval.
