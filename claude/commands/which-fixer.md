---
description: Fix restrictive "which" clauses to "that" in comments and docs (bulk on the first run, incremental afterwards).
allowed-tools: Read, Edit, Write, Grep, Glob, Bash(git diff:*), Bash(git ls-files:*), Bash(git status:*), Bash(cmp:*)
model: sonnet
---

Follow the `which-fixer` skill exactly:

- Skill: `.agents/skills/which-fixer/SKILL.md`
- Mode is automatic: bulk when `.agents/memory/which-fixer-applied.md` is
  absent, incremental otherwise. Do not ask which mode to use.
- Scope: project-owned files only, per the skill's submodule and
  config-distributed skip rules.
- Honor every guard in the skill (comma, parenthesis/dash, preposition,
  interrogative, sentence-initial, hyphenated identifier, fixed phrases).
  When uncertain, leave the occurrence unchanged and record it in
  `Skipped[]` — a missed case beats a wrong fix.
- Never touch code: string literals, identifiers, fenced or indented code
  blocks, inline code spans, or snippets embedded in doc comments.
- Report: Mode, FilesScanned, FilesChanged, Replacements[], Skipped[].
