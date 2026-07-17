---
description: >
  Fix English grammar, punctuation, and spelling errors in the comments and
  documentation of this repository, per the shared error catalog.
allowed-tools: >-
  Read, Edit, Write, Grep, Glob, Bash(git diff:*), Bash(git ls-files:*),
  Bash(git status:*), Bash(cmp:*)
model: sonnet
---

Follow the `proofread` skill exactly:

- Skill: `.agents/skills/proofread/SKILL.md`
- Catalog of rules and guards: `.agents/guidelines/english-style.md`. The
  skill applies it; it invents no rules of its own.
- Mode comes from the argument: no argument scans the current branch's
  changes; `all` sweeps every project-owned file (and runs the legacy
  `which-fixer` cleanup); a path scopes the sweep to that directory.
- Scope: project-owned files only, per
  `.agents/guidelines/project-owned-files.md` — skip submodule contents and
  config-distributed files.
- Edit prose only: comment text and Markdown/AsciiDoc body. Never touch
  string literals, identifiers, code blocks, inline code spans, or the
  machine-read comment directives listed under the catalog's "Never edit" section.
- Honor every leave-alone guard in the catalog. When uncertain whether an
  occurrence is an error, leave it unchanged and record it in `Skipped[]` —
  a missed case beats a wrong fix.
- Report per the skill: Mode, FilesScanned, FilesChanged, Changes[] grouped
  by catalog topic (file, line, before → after), Skipped[] (file, line,
  topic, reason), and LegacyCleanup in `all` mode.
