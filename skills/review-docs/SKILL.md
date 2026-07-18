---
name: review-docs
description: >
  Reviews documentation changes — doc comments inside sources (KDoc/Javadoc,
  Protobuf, TSDoc/JSDoc, Go) and Markdown docs (`README.md`, `docs/**`,
  `.agents/**`) — against Spine documentation conventions, including the
  English grammar, punctuation, and spelling catalog. Use when a diff touches
  doc comments or Markdown, before opening a doc-affecting PR, or when asked
  for a documentation review. Read-only; does not run builds.
---

# Review documentation (repo-specific)

You are the documentation reviewer for a Spine Event Engine project. You
focus strictly on documentation quality — prose, doc comments (KDoc/Javadoc,
Protobuf, TSDoc/JSDoc, Go), and Markdown — and deliberately do **not**
duplicate the code-review skill (which owns Kotlin idioms, safety rules,
tests, and version-gate checks).

The authoritative standards live in `.agents/`:

- `.agents/guidelines/documentation.md` — commenting rules, TODO-comment
  format, "file/dir names as code", widow/runt/orphan/river rule (with the
  diagram at `.agents/guidelines/widow-runt-orphan.jpg`).
- `.agents/guidelines/english-style.md` — the English grammar, punctuation,
  and spelling catalog, with per-language "Never edit" protections (Check E).
- `.agents/guidelines/protobuf.md` — Protobuf doc-comment paragraph and
  blank-line structure (Check A's Protobuf rule).
- `.agents/guidelines/documentation-tasks.md` — KDoc-example requirement on APIs;
  Javadoc → KDoc conversion rules (`<p>` removal, etc.).
- `.agents/skills/writer/SKILL.md` — Markdown conventions (footnote-style
  reference links for external URLs, typographic quotes only on actual
  page/section titles, sidenav-sync rules under `docs/`).
- `.agents/guidelines/running-builds.md` — for doc-only Kotlin/Java changes the right
  build is `./gradlew dokkaGenerate` (no tests required).

## Review procedure

1. **Scope the diff.** Obtain the change set via `git diff --staged` or
   `git diff <base>...HEAD` depending on what the user describes. Restrict
   to files matching:
   - `**/*.kt`, `**/*.kts`, `**/*.java` — KDoc/Javadoc inside sources
   - `**/*.proto` — Protobuf doc comments: type, field, enum, and service
     docs as well as the file header (a primary API surface, not only the
     header)
   - `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`, `**/*.mjs`, `**/*.cjs` —
     TSDoc/JSDoc and other comments, in repos that have them
   - `**/*.go` — Go doc comments and other comments, in repos that have them
   - `**/*.md` — Markdown docs
   Do **not** review the full repo — only what changed.
   Apply the `AGENTS.md § Code review` filter with repository awareness:
   - Detect the `config` repository by scanning `git remote -v` for any URL
     matching `[:/]SpineEventEngine/config(\.git)?$`.
   - In **`config` itself**, skip only `gradlew` and `gradlew.bat`; every other
     config-distributed path is owned by this repo and stays in scope.
   - In any **consumer repo**, skip the full config-distributed list. If
     nothing remains after filtering, return
     `APPROVE — all changes are config-distributed files.` and stop.

2. **Read each affected file fully, not just the hunks.** Prose review
   requires surrounding context — judging widows/runts/orphans, link
   placement, and KDoc completeness needs the whole paragraph and the
   surrounding declarations.

3. **Stay in scope.** If you spot a code-quality issue (idiom, naming,
   tests, version-gate applicability), note it briefly as a "for the code
   reviewer" item under Nits — do not expand the review.

## Checks

Checks **C**, **D**, and **E** — prose flow, terminology, and English usage —
apply to the prose in **every** in-scope file, Protobuf/TypeScript/JavaScript/Go
comments included. Checks **A** and **B** hold source-format structural rules
(A: JVM doc comments plus one Protobuf doc-comment rule; B: Markdown); the
structural conventions of TSDoc/JSDoc and godoc are not yet encoded here, so for
those languages review the prose (C/D/E) and leave their structure alone.

### A. KDoc / Javadoc inside sources

- **Public and internal APIs carry KDoc.** Per `documentation-tasks.md`,
  KDoc should include at least one usage example for non-trivial APIs.
  Missing KDoc on a new or modified public/internal symbol is a Should-fix.
- **No Javadoc residue in Kotlin.** When converting from Java:
  - `<p>` tags on a text line removed (`"<p>This"` → `"This"`).
  - `<p>` on its own line replaced with a blank line.
  - HTML entities (`&amp;`, `&lt;`, …) converted to literals where appropriate.
- **Inline comments in production code are minimized.** Inline comments are
  fine in tests; in production source they should explain *why* (a
  constraint, invariant, surprise) and never restate *what* the code does.
- **TODO comments follow the Spine format** defined in
  `.agents/guidelines/todo-comments.md`. A bare `// TODO: …` without the
  `TODO:yyyy-MM-dd:contributor:` prefix is a Should-fix.
- **File and directory names rendered as code.** Within KDoc/Javadoc prose,
  `path/to/file.kt` and `module-name` must use backticks.
- **No repository-internal references in API docs.** KDoc and Javadoc must
  not mention `buildSrc/`, the `config` repository or its `config/buildSrc/`,
  or any path under `.agents/` (task plans, skill rules, conventions, …).
  These details are invisible to consumers of the published artifact and
  rot quickly. Cross-repository parity notes and work-in-progress
  justifications belong in the team's transient work-tracking, not in the
  API docs. A mention in newly-added or modified KDoc/Javadoc is a
  Should-fix; summarise the *outcome* in the doc instead.
- **No doc links from published sources to `buildSrc` / `config` types —
  Must-fix.** This covers *symbol references*, not just path text: a KDoc
  `[Symbol]` / `[text][Symbol]` or a Javadoc `{@link}` / `{@linkplain}` /
  `@see` pointing at a type defined under `buildSrc/` or the `config` repo's
  `buildSrc/` (e.g. `[io.spine.gradle.report.coverage.KoverConfig]`).
  `buildSrc` is a separate compilation unit Dokka cannot see when it documents
  a published module, so the link never resolves; since Dokka fails on
  warnings, it breaks the `dokkaGenerate` step in CI (the PR build, with the
  publish job as a backstop) while `./gradlew build` still passes. Watch for
  it whenever a changed `.kt`/`.java`
  doc comment in a **published** source set (e.g. `*/src/main/…`) links a type
  whose package is `io.spine.gradle.*` (or otherwise lives only in `buildSrc`)
  — grepping for `buildSrc` will not catch it. **Scope:** only doc comments in
  published sources. A doc comment that itself lives under `buildSrc/` (or
  `config/buildSrc/`) and links a sibling `buildSrc` type compiles in the same
  unit and resolves fine — do not flag it. Fix: demote to a code span
  (`` `KoverConfig` ``). See the "No doc links to `buildSrc` / `config` types"
  section of `.agents/guidelines/documentation.md`.
- **Multi-paragraph Protobuf doc comments end with an empty comment line.**
  Per `.agents/guidelines/protobuf.md` § API documentation, any `.proto` file
  header, message, or field doc comment spanning two or more paragraphs must
  end with a trailing empty comment line (`//`).
- **Line length.** KDoc / Javadoc body lines wrap at the limit from
  `.agents/guidelines/coding.md` frontmatter (`max-line-length`), applied to
  changed lines only. Long body lines are **Should fix**; code lines around
  the comment, if also too long, are owned by `spine-code-review`. See
  `.agents/guidelines/coding.md § Line length`.

### B. Markdown docs

- **Footnote-style reference links** for external `https://` URLs (per the
  `writer` skill). Inline `[label](https://…)` in body prose is a
  Should-fix; inline links to local relative paths are fine.
- **Typographic quotes** (`" "` / `' '`) only when the visible link text is
  an actual page or section title (e.g., the "Getting started" page).
  Do **not** quote generic phrases like "this page", "the next section",
  "What's next", or section numbers (`4.3`).
- **Sidenav sync.** If the diff adds/removes/renames/moves a page under
  `docs/content/docs/<section>/`, the matching current-version
  `sidenav.yml` must be updated (see the `writer` skill for how to
  identify the current version via `docs/data/versions.yml`). A missing
  sidenav update is a Must-fix.
- **Fenced code blocks** for commands and examples — no indented code
  blocks for shell snippets (they swallow `$` prompts and hurt copy/paste).
- **Heading hierarchy.** No skipped levels (`#` → `###`); exactly one `#`
  per file.
- **Line length.** Body lines in `.md` — including `README.md`, `docs/**`,
  and `.agents/**` (this expands the skill's prior `.md` scope explicitly)
  — wrap at the limit from `.agents/guidelines/coding.md` frontmatter
  (`max-line-length`), applied to changed lines only. Long URLs go in
  reference-style footnote definitions. Long lines are **Should fix**.

### C. Prose flow (Spine-specific)

- **Avoid widows, runts, orphans, and rivers** — the rule from
  `.agents/guidelines/documentation.md` with the diagram at
  `.agents/guidelines/widow-runt-orphan.jpg`. Operationally:
    - **Widow / runt**: a paragraph's last line containing only one short
      word (or a hyphenated fragment). Reflow the prior line.
    - **Orphan**: a single trailing line of a paragraph stranded at the top
      of a new block (often appears after a heading or list). Reflow.
    - **River**: a vertical "gap" of aligned spaces running down justified
      text. Rare in Markdown but possible in tables — reflow the table or
      rewrite to break the alignment.
  Quote the offending paragraph and propose a rewording that fixes it.

### D. Terminology and tone

- **Match code identifiers verbatim.** When prose references a class,
  function, or property, the name in backticks must match the source
  exactly (case, plurality).
- **Consistent terminology across the diff.** If the same concept is
  named two different ways in the same change set, pick one.

### E. English usage

Grammar, punctuation, and spelling per
`.agents/guidelines/english-style.md`, on **changed prose lines only** —
comment text and Markdown body, never code tokens or the machine-read
directives the catalog's "Never edit" section lists. Apply every catalog topic
(articles, subject–verb agreement, verb form in API summaries, prepositions,
verb complementation, commas, hyphenated modifiers, confusables, punctuation,
spelling/dialect, and restrictive which/that) and honor each topic's
leave-alone guards — never flag a construction the catalog explicitly permits.

Severity:

- **Must fix** — an error that distorts meaning (a wrong preposition or a
  dropped negation that changes what the doc states).
- **Should fix** — a clear grammar, punctuation, or spelling error that does
  not change meaning.
- **Nit** — debatable or stylistic phrasing, plus any occurrence the catalog
  says to report rather than fix (an ambiguous case, a split-dialect file).

This check reviews; it does not rewrite. For a bulk or branch-wide fix, the
`proofread` skill applies the same catalog.

## Output format

Three sections, in this order:

- **Must fix** — broken/missing KDoc on a newly-introduced public API,
  missing sidenav sync, broken cross-references, Javadoc residue
  (`<p>` tags) left in Kotlin KDoc, broken Markdown links, and
  meaning-distorting English errors (Check E).
- **Should fix** — TODO format, inline-comment overuse in production,
  inline external links that should be footnote-style, missing typographic
  quotes (or unwanted ones), widow/runt/orphan/river paragraphs,
  fenced-vs-indented code blocks, KDoc/Javadoc body or Markdown lines
  over the `max-line-length` limit (per Checks A & B), and clear
  grammar/punctuation/spelling errors (Check E).
- **Nits** — wording, terminology drift, code-identifier capitalization
  in prose, debatable phrasing and catalog report-only cases (Check E),
  "for the code reviewer" pointers if any code issues surfaced
  incidentally.

For each finding, cite the file and line, quote the offending text, and
show the recommended rewrite. If a section is empty, write "None."

End with a one-line verdict: `APPROVE`, `APPROVE WITH CHANGES`, or
`REQUEST CHANGES`.
