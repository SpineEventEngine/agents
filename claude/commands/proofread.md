---
description: >
  Fix English grammar, punctuation, and spelling errors in the comments and
  documentation of this repository, per the shared error catalog.
argument-hint: "[all | <path>]"
allowed-tools: >-
  Read, Edit, Write, Grep, Glob, Bash(git diff:*), Bash(git ls-files:*),
  Bash(git status:*), Bash(git rm:*), Bash(rm:*), Bash(cmp:*)
model: sonnet
---

Follow the `proofread` skill exactly:

- Skill: `.agents/skills/proofread/SKILL.md`
- Catalog of rules and guards: `.agents/guidelines/english-style.md`. The
  skill applies it; it invents no rules of its own.
- Argument: $ARGUMENTS
  - Empty: scan the files changed on the current branch.
  - `all`: sweep every project-owned file, then run the legacy `which-fixer`
    cleanup — delete `.agents/memory/which-fixer-applied.md` and remove its
    pointer line from `.agents/memory/MEMORY.md` when present.
  - A path: scope the sweep to that directory or file.
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
