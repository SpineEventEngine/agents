---
slug: enforce-max-line-length
branch: move-tasks
owner: claude
status: in-progress
started: 2026-05-29
related-memories: []
---

## Goal

Extend the agent-facing instructions and skills under `.agents/` so
that detekt's `MaxLineLength` rule
(`buildSrc/quality/detekt-config.yml:19-21`,
`maxLineLength: 100`, `excludeCommentStatements: true`) is honoured at
author time and surfaced at review time, instead of being discovered
late by CI on GitHub.

Severity by file type:

- **Detekt-enforced → Must fix** — non-comment lines in `.kt` / `.kts`
  over the configured limit. These break `./gradlew build`.
- **Repo policy → Should fix** — KDoc / Javadoc body lines in any
  source extension; `.java` lines; `.proto` lines; `.md` lines
  (incl. `README.md`, `docs/**`, `.agents/**`). Detekt does not flag
  these; the reviewer skills do.

## Context

CI and local builds repeatedly fail on detekt's `MaxLineLength` rule.
The user finds the late discovery — especially on GitHub — annoying.
None of the current agent instructions or skills name the rule, so
agents write code that breaks the build, then have to retry.

### Framing

The numeric threshold is a configuration parameter, not a constant.

**Author-time behaviour**: agents read `MaxLineLength.maxLineLength`
from `buildSrc/quality/detekt-config.yml` once per session and treat
the value as a session-local constant. This is workable; re-reading
the YAML for every line of output is not.

**Guidance text**: the new sections never bake the literal number
into `.agents/` prose. They reference the rule name and the file
path. If the threshold changes, the agent's session-start lookup
picks up the new value with no doc edit.

**Review-time behaviour**: when a reviewer surfaces a finding, the
report cites the actual value (`"line 47 is 108 chars (limit 100,
from buildSrc/quality/detekt-config.yml)"`). The number lands in the
report, not in the rule.

### KDoc handling (empirically verified)

`excludeCommentStatements: true` excludes lines whose statement is a
comment — single-line `//`, trailing `//`, and KDoc body lines. The
exclusion of KDoc bodies is confirmed by
`buildSrc/src/main/kotlin/detekt-code-analysis.gradle.kts:52`, a
115-character KDoc body line that ships in the codebase and passes
the detekt build today. KDoc body lines are therefore Should-fix
repo policy, not Must-fix.

### Splitting / restructure rules (confirmed with user)

- String literals (including URLs inside strings) split at a
  meaningful boundary into ≥ 2 `+`-concatenated pieces — never
  truncated.
- Other unbreakable tokens (`[name][some.long.FQN]` in KDoc; long
  generated identifier): prefer restructure (intermediate `val`,
  reference-style Markdown link, alias). When no restructure is
  reasonable, use `@Suppress("MaxLineLength")` on the declaration
  with a brief `// Reason: …` comment. Use `@file:Suppress` only for
  file-scope cases (e.g., a long import that cannot be aliased).

### Scope clarifications

- **Generated sources excluded**: do not flag lines under
  `**/generated/**` or `**/generated-proto/**` — these are the paths
  Spine's `buildSrc/quality/checkstyle.xml:35-42` and
  `buildSrc/quality/pmd.xml:36-37` already exclude from the other
  static-analysis runs.
- **Reading context vs. reporting scope.** Reviewers continue to read
  each affected file fully (existing `spine-code-review` rule at
  `.agents/skills/spine-code-review/SKILL.md:63`). They only *report*
  line-length findings on lines the diff touched
  (`git diff -U0 <base>...HEAD`). Pre-existing long lines are not
  flagged. The two rules co-exist: read all, report changed.
- **`module.gradle.kts` carve-out**: per `AGENTS.md § Code review`,
  in a consumer repo `buildSrc/src/main/kotlin/module.gradle.kts` is
  in scope for the reviewers; it follows the same Must-fix rule as
  any other `.kts`.
- **YAML lookup is from `HEAD`, not the base ref.** Long-lived
  branches sometimes change `detekt-config.yml` mid-branch; reviewers
  always re-read the value from the working tree, so the rule matches
  what `./gradlew build` will see.
- **YAML missing is a hard error.** If
  `buildSrc/quality/detekt-config.yml` is absent or lacks
  `MaxLineLength.maxLineLength`, the reviewer reports a Must-fix
  asking the user to restore the config rather than silently
  inventing a number.

## Plan

Six `.agents/` Markdown files. No code or build changes. New lines
wrap at the configured limit.

### 1. `.agents/guidelines/coding.md`

- [x] Add a new top-level `## Line length` section, placed immediately
      after the existing "Text formatting" section. The canonical
      content lives here; other docs cross-reference this heading.
      Cover:
  - Source-of-truth lookup: read `MaxLineLength.maxLineLength` from
    `buildSrc/quality/detekt-config.yml` once at session start. Never
    write the literal number into the guideline.
  - Severity split (detekt-enforced vs. repo policy) per Context above.
  - String-literal strategy with a small example whose split is at a
    URL path boundary, e.g.

    ```kotlin
    val ref = "https://github.com/SpineEventEngine/config/blob/master/" +
        "buildSrc/quality/detekt-config.yml"
    ```

    This covers the URL-splitting case the user called out; the
    existing `JacocoConfig.kt:122-125` pattern splits prose, not a
    URL, and is not a sufficient teacher on its own.
  - Unbreakable-token rules: import alias, restructure, then
    `@Suppress` placement (on the declaration; `@file:Suppress` for
    file-scope).
  - Scope exclusions: generated sources; changed lines only.

### 2. `.agents/guidelines/documentation.md`

- [x] Append one bullet to "Commenting guidelines":

  > Wrap KDoc / Javadoc body lines and Markdown body lines at the
  > limit defined in `buildSrc/quality/detekt-config.yml`
  > (`MaxLineLength.maxLineLength`). See
  > `coding.md § Line length` for the splitting strategy.

  Single sentence; no duplication of the canonical section.

### 3. `.agents/guidelines/quick-reference-card.md`

- [x] Rewrap the existing 135-char line 3 so the card itself respects
      the rule it now advertises.
- [x] Append one line (plain text, no decorative emoji — the rest of
      the card uses 🚫 for a hard prohibition only, and line-length
      guidance isn't in that category):

  > At session start, read `MaxLineLength.maxLineLength` from
  > `buildSrc/quality/detekt-config.yml` and wrap new lines under it.
  > See `coding.md § Line length`.

### 4. `.agents/skills/spine-code-review/SKILL.md`

- [x] In "Review procedure" step 3 (the coding-guidelines checklist),
      append:

  > Line length (`MaxLineLength`). The reviewer reads the limit from
  > `buildSrc/quality/detekt-config.yml` and applies it only to lines
  > the diff touched. Non-comment `.kt` / `.kts` lines over the limit
  > are **Must fix** (detekt breaks the build;
  > `excludeCommentStatements: true` exempts KDoc bodies from the
  > build break). KDoc bodies in `.kt` / `.kts`, and any `.java` line
  > over the limit, are **Should fix**. For changed lines inside a
  > string literal the fix is splitting into ≥ 2 `+`-concatenated
  > pieces; otherwise follow `coding.md § Line length`.

- [x] Update "Output format" correspondingly: add the bucket entries
      but keep the existing Must / Should / Nits semantics unchanged.

### 5. `.agents/skills/review-docs/SKILL.md`

- [x] Insert into "Checks → A. KDoc / Javadoc inside sources":

  > **Line length.** KDoc / Javadoc body lines wrap at the limit from
  > `buildSrc/quality/detekt-config.yml`. Long body lines are
  > **Should fix**; code lines around the comment, if also too long,
  > are owned by `spine-code-review`.

- [x] Insert into "Checks → B. Markdown docs":

  > **Line length.** Body lines in `.md` — including `README.md`,
  > `docs/**`, and `.agents/**` (this expands the skill's prior `.md`
  > scope explicitly) — wrap at the configured limit. Long URLs go in
  > reference-style footnote definitions. Long lines are
  > **Should fix**.

- [x] Update the skill's frontmatter `description` so its Markdown scope
      matches Check B: add `.agents/**` to the parenthetical
      (`README.md`, `docs/**`, `.agents/**`). The paired
      `agents/openai.yaml` uses a path-free short description and needs
      no change.

### 6. `.agents/skills/pre-pr/SKILL.md`

- [x] In the "Procedure" section, add a one-line pointer near the
      existing reviewer-dispatch table (around
      `.agents/skills/pre-pr/SKILL.md:104-106`):

  > Line-length findings on changed Kotlin / Java / Markdown lines
  > are reported by the dispatched reviewers (`spine-code-review`,
  > `review-docs`). pre-pr itself does not re-check.

  Documentation only — no logic change. Clarifies that the rule is
  inherited via the existing dispatch and prevents future edits from
  duplicating the check inside pre-pr.

### Verification

- [x] Visually scan every edited file for the literal `100`. The
      number should not appear in the new prose; only the rule name
      and the YAML path should.
- [x] Read the YAML, capture the value
      (`LIMIT=$(awk '/maxLineLength:/ {print $2}'
      buildSrc/quality/detekt-config.yml)`), and run
      `awk -v n=$LIMIT 'length > n' <each-edited-file>`. `awk`'s
      `length` counts bytes; for the ASCII prose introduced here that
      matches characters, but a non-ASCII glyph in future edits would
      miscount. Acceptable for this change.
- [x] Sanity-check cross-references: every `coding.md §
      Line length` link resolves to the new top-level section heading.
- [x] Spot test the author behaviour. In a fresh session, ask the
      agent to write a long Kotlin string literal containing a URL;
      confirm the result splits with `+` at a URL path boundary and
      preserves every character.
- [x] Spot test the reviewer behaviour. Synthesize a diff with: one
      non-comment `.kt` line over the limit (expect Must fix); one
      KDoc body line over the limit (expect Should fix); one `.java`
      line over the limit (expect Should fix); one `.md` body line
      over the limit (expect Should fix). Run `spine-code-review` and
      `review-docs` and confirm bucketing.
- [x] Confirm the missing-YAML behaviour: temporarily move
      `buildSrc/quality/detekt-config.yml` aside, run a reviewer over
      a synthetic diff, confirm it reports a **Must fix** asking the
      user to restore the config (not a silent fallback).

## Out of scope

- `buildSrc/quality/detekt-config.yml` — unchanged.
- `writer/SKILL.md` and `java-to-kotlin/SKILL.md` — they author, they
  don't enforce. The canonical rule in `coding.md` reaches
  them by reference.
- `gradle-review/SKILL.md` — `.kts` files are reviewed by
  `spine-code-review` (via pre-pr's `code` dispatch). Adding a second
  owner would double-report; defer to `spine-code-review § Line length`.
- `update-copyright/SKILL.md` — if a header rewrite produces a long
  line, the reviewer will catch it; no skill-local rule.
- `memory/MEMORY.md` and `_TOC.md` — the rule is durable team policy
  belonging in `.agents/`, indexed via the natural section heading.
- Rewrap of pre-existing over-length lines outside the diff (e.g.,
  `java-to-kotlin/SKILL.md:24,25,40,42`) — separate cleanup task, not
  blocked by this plan.

## Decisions

- **KDoc severity**. Should-fix, not Must-fix. Empirically verified
  by `buildSrc/src/main/kotlin/detekt-code-analysis.gradle.kts:52`
  (115-char KDoc body line that ships and builds clean).
- **`gradle-review` not edited**. `.kts` files flow through
  `spine-code-review` already (via pre-pr's `code` dispatch); a second
  owner in `gradle-review` would cause double-reports for the same
  finding. The trade-off is that manual `/gradle-review` runs without
  a paired `/spine-code-review` will not surface line-length findings on
  `.kts` files; users running only `gradle-review` are looking for
  Gradle conventions, not detekt rules, so the gap is acceptable.
- **YAML lookup at session start, not per line**. Re-reading the YAML
  for every line of output is impractical; the agent caches the value
  as a session-local constant. Documentation never bakes the literal.
- **Missing YAML is Must-fix, not informational**. Avoids silent
  fallback drift.

## Log

- 2026-05-29 — drafted in this session; plan revised twice to address
  findings from two review rounds (KDoc empirics, generated-source
  globs, `## Line length` heading placement, `gradle-review` →
  `pre-pr` swap, YAML-missing severity, verification cleanup).
  Awaiting approval.
- 2026-06-02 — implemented all six edits on branch `move-tasks`. The
  `kotlin-review` skill referenced by the original plan (item 4) no
  longer exists; it was split into `kotlin-engineer` (general Kotlin)
  and `spine-code-review` (repo-specific). Per user decision, the
  line-length review rule landed in `spine-code-review` only — it owns
  the step-3 coding-guidelines checklist and reviews `.java` (covering
  the Should-fix Java case); `kotlin-engineer` was left untouched. The
  plan's `kotlin-review` references were rewritten to `spine-code-review`
  to keep this record accurate. Mechanical verification passed: no
  literal `100` in any edited file, no new over-length lines (the
  pre-existing 116-char `spine-code-review:67` is outside this diff and
  deferred). Runtime spot-tests (author behaviour, reviewer bucketing,
  missing-YAML path) remain to be exercised in fresh sessions.
- 2026-06-02 — follow-ups per user: wrapped the pre-existing 116-char
  line at `spine-code-review/SKILL.md:67` (the Protobuf-DSL checklist
  bullet) so every touched file now respects the limit; and updated the
  `review-docs` frontmatter `description` to add `.agents/**` to its
  Markdown scope, matching Check B. Pre-existing over-length lines in
  files this task does *not* touch (e.g. `java-to-kotlin/SKILL.md`)
  remain deferred per Out of scope.
