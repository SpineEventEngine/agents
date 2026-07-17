---
slug: english-usage-improvements
branch: doc-review-improvements
owner: claude
status: in-progress
started: 2026-07-17
---

## Goal

Establish a single, evolving English-usage standard for the organisation and
wire it into both remediation (the `proofread` fixer skill — replacing
`which-fixer` and covering the full grammar/punctuation scope) and prevention
(the `review-docs` reviewer and the doc-authoring skills), so existing repos
get cleaned up once and new changes are held to the standard afterwards.

## Context

- An ad-hoc Sonnet run over `core-jvm` found dozens of grammar and punctuation
  errors in Javadoc/KDoc; other repos are expected to be similar.
- Today only one English rule is encoded anywhere: the which/that rule in
  `skills/which-fixer/`. `review-docs` checks Spine conventions (structure,
  links, line length, widows/runts) but has **no** grammar or punctuation
  checks; `guidelines/` has no English-usage page.
- Scope spans every language carrying API documentation in the org:
  Kotlin/Java (KDoc/Javadoc), Protobuf (type and field doc comments — a
  primary API surface), TypeScript/JavaScript (TSDoc/JSDoc), Go (doc
  comments), and Markdown prose.
- This repo floats to every consumer, so anything landed here ships org-wide.
- Delivery/rollout automation (running the sweep across ~40 repos) is a
  separate follow-up discussion — out of scope for this task.

## Plan

- [x] **Phase 1 — the standard.** Create `guidelines/english-style.md` (name
      parallels `kotlin-code-style.md` / `java-code-style.md`): the error
      catalog grouped by topic — articles, subject–verb agreement,
      prepositions, comma rules, hyphenated compound modifiers, "allows to",
      its/it's, verb form in API summaries, punctuation mechanics, spelling —
      each topic with before → after examples and leave-alone guards, at the
      rigor level of `which-fixer`'s guard list.
  - [x] Seed the topics from the grouped report of the `core-jvm` Sonnet
        session (user to share it) plus recurring Russian-speaker error
        classes.
  - [x] Migrate the which/that rule from `which-fixer` as a catalog topic,
        preserving its full guard list (comma, parenthesis/dash, preposition,
        interrogative/determiner, sentence-initial, hyphenated identifier,
        fixed phrases).
  - [x] Dialect policy (decided 2026-07-17): the unit of consistency is the
        file — align a clear outlier to the file's dominant dialect; when no
        dialect clearly dominates, report the mix and leave the text alone.
        No org-wide dialect conversion; a standard may be forced later.
  - [x] Add a "Comment mechanics per language" section: where English prose
        lives in each language (KDoc/Javadoc; Protobuf `//` doc comments per
        `protobuf.md`; TSDoc/JSDoc descriptions; Go doc comments) and what
        is machine-directed and must never be edited — `//go:*` pragmas,
        `// +build` constraints, Go `Deprecated:` markers and the godoc
        leading-identifier convention, `@ts-ignore` / `@ts-expect-error` /
        `@ts-nocheck`, triple-slash references, eslint/prettier/istanbul
        directives, webpack magic comments, JSDoc tags and `{Type}` braces,
        `buf:lint:ignore`.
  - [x] Index in `guidelines/_TOC.md`; link from `documentation.md`,
        `kdoc.md`, `javadoc.md`, and `protobuf.md`.
- [x] **Phase 2 — the fixer.** New skill `proofread`, replacing
      `which-fixer`: stateless, with the mode chosen explicitly by the
      caller — the default run scans the files changed on the current branch
      (union of `origin/master...HEAD` and working-tree diffs,
      `--diff-filter=ACMR`); an `all` parameter sweeps all the project-owned
      code and docs, module by module. No `.agents/memory/` sentinel — the
      per-repo "swept already" fact lives in the rollout tracking, not in
      repo state. Project-owned file scoping, comments-and-prose-only
      editing discipline, conservative when-uncertain-skip bias, and a
      report grouped by catalog topic (the learning loop).
  - [x] File scope: `.kt`, `.kts`, `.java`, `.proto`, `.md`, `.adoc`, plus
        `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, and `.go`.
  - [x] Retire `which-fixer`: delete `skills/which-fixer/` and
        `claude/commands/which-fixer.md`; swap the `which-fixer` example in
        `docs/authoring-skills.md` (line ~98, sonnet tier) for `proofread`.
        The which/that guard list migrates into the catalog (Phase 1) — no
        other references exist outside the skill's own directory. (The
        `english-style.md` hyphenated-identifier guard keeps `which-fixer`
        as its illustrative example — a valid teaching case, not a live
        cross-reference.)
  - [x] Legacy cleanup in `all` mode: if the target repo carries the
        obsolete `.agents/memory/which-fixer-applied.md`, delete it and its
        pointer line in `.agents/memory/MEMORY.md`.
  - [x] Optional refactor: extract the shared project-owned-files scoping
        into `guidelines/project-owned-files.md`, referenced by `proofread`
        and `update-copyright`. `update-copyright`'s skip is implemented in
        its Python script, so it keeps its own list and gains a
        cross-reference; behavior unchanged.
  - [x] Accept an optional path argument to scope a sweep to one module —
        useful for staging `all` over very large repos.
  - [x] Wrappers: `claude/commands/proofread.md` (model: sonnet) and
        `skills/proofread/agents/openai.yaml`. No subagent wrapper — fixers
        are commands in this repo.
- [x] **Phase 3 — the reviewer.** Add a check section "E. English usage" to
      `skills/review-docs/SKILL.md`, referencing the catalog; changed prose
      lines only. Severity: clear grammatical errors → Should fix; ambiguous
      or debatable phrasing → Nits; meaning-distorting errors → Must fix.
  - [x] Widen `review-docs` Protobuf coverage from "file-level documentation
        headers" to all doc comments — type and field docs are a primary API
        surface, with structure rules already in
        `.agents/guidelines/protobuf.md`.
  - [x] Add `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, and `.go` to the
        `review-docs` scope. Prose-flow, terminology, and English-usage
        checks apply to every language; structural checks stay per-language
        (KDoc/Javadoc today; TSDoc/JSDoc and godoc structure notes can come
        later). Added a `## Checks` preamble marking C/D/E language-agnostic
        and A/B JVM/Markdown-specific; mirrored the wider scope in the
        `review-docs` agent wrapper's description.
  - [x] Clarify `pre-pr` dispatch: `review-docs` runs when any changed hunk
        touches doc-comment lines in any supported language — including
        mixed code + comment changes and `.proto` edits (today a proto
        change triggers the build but no doc reviewer explicitly).
- [ ] **Phase 4 — prevention at authoring time.** Add language-quality
      pointers to the catalog in `writer` and `java-to-kotlin` (the
      Javadoc → KDoc conversion is the natural moment to also fix old prose).
- [ ] Validate per `docs/authoring-skills.md` checklist; open a PR.

## Log

- 2026-07-17 — analysed current assets; drafted this plan, awaiting review.
- 2026-07-17 — widened scope per user notes: full `.proto` doc-comment
  coverage, plus TypeScript/JavaScript/Go doc comments across the fixer and
  the reviewer.
- 2026-07-17 — decision: retire `which-fixer` in favour of `proofread`; no
  `.agents/memory/` mode sentinel. Default mode scans branch-changed files;
  the explicit `all-files` parameter runs the full sweep (module by module),
  applied once per repo after the latest `config` pull.
- 2026-07-17 — dialect policy decided: per-file consistency — align clear
  outliers to the file's dominant dialect, report when dominance is unclear;
  an org-wide standard may be forced later.
- 2026-07-17 — renamed the full-sweep parameter `all-files` → `all`: it
  means all project-owned code and docs, not literally every file.
- 2026-07-17 — Phase 1 approved and implemented: `guidelines/english-style.md`
  created with 11 catalog topics, per-language comment mechanics, and the
  migrated which/that guard list; indexed in `_TOC.md` and linked from
  `documentation.md`, `kdoc.md`, `javadoc.md`, and `protobuf.md`. The
  `core-jvm` grouped report was not available, so the catalog is seeded from
  recurring Russian-speaker error classes; the report can extend it later.
- 2026-07-17 — `review-docs` reviewed Phase 1: which/that migration and
  linguistics confirmed sound; fixed its findings — deterministic "listens
  to" row plus a "listens for" guard, an AsciiDoc "Never edit" subsection,
  two over-long table rows, three widow paragraphs, a missing article in
  `kdoc.md`, "provides the possibility to" demoted from auto-fix to
  report-only, dialect self-consistency (`behaviour`), and c8/v8 coverage
  markers added.
- 2026-07-17 — re-review verdict: APPROVE. All fixes independently
  re-verified by `review-docs`; the last cosmetic nit (comment word order
  in the prose-location table) is fixed. Phase 1 is done; changes are
  staged, awaiting commit/PR authorization.
- 2026-07-17 — Phase 1 committed (`ac097c4`).
- 2026-07-17 — Phase 3 implemented and committed after two review passes.
  Re-verify verdict: APPROVE WITH CHANGES — all substantive items confirmed
  fixed; closed the final nits (fourth wrapper's catalog naming, and scoped
  the `pre-pr` dispatch honestly to the JVM/Protobuf/Markdown files step 1
  classifies rather than over-promising TS/JS/Go). Added Check E
  (English usage) to `review-docs` with the plan's severity mapping; widened
  its scope to full Protobuf doc comments plus TS/JS/Go; added a `## Checks`
  language-agnostic preamble; wired `protobuf.md` structure into Check A;
  broadened the `pre-pr` review-docs dispatch (proto + mixed code+comment).
  `review-docs` re-reviewed: caught stale wrapper twins
  (`claude/commands/review-docs.md`, `skills/review-docs/agents/openai.yaml`,
  `claude/commands/pre-pr.md`), a missing "verb form in API summaries" topic
  in Check E, an over-claimed AsciiDoc scope, and a Protobuf structural gap —
  all fixed. Phase 2 committed as `407ff52`; Phase 1 as `ac097c4`.
- 2026-07-17 — Phase 2 implemented: `skills/proofread/` (SKILL.md +
  `agents/openai.yaml`), `claude/commands/proofread.md` (sonnet), the
  extracted `guidelines/project-owned-files.md` (TOC entry 19), a
  cross-reference in `update-copyright`, and the `which-fixer` retirement
  (skill dir + command deleted, `authoring-skills.md` tier example
  swapped). `review-docs` verdict: APPROVE WITH CHANGES — extraction
  fidelity, git/mode logic, legacy cleanup, and retirement all verified
  correct; fixed its findings (a wrong `module.gradle.kts` path in
  `update-copyright`, six widow lines, terminology drift, a dropped
  `config:replaces` detail, and the wrapper checkbox). Staged, awaiting
  commit authorization.
