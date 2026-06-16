---
name: which-fixer
description: >
  Fixes the "which/that" grammar error in source-code comments and documentation.
  Replaces restrictive "which" clauses (no preceding comma) with "that", leaving
  non-restrictive ", which" clauses untouched. Touches *project-owned* sources
  only — never submodule contents or files distributed by the `config` repository
  (such as `buildSrc/` and the org-wide root docs). Runs in two modes: bulk (first
  run, all project-owned files) and incremental (subsequent runs, modified files
  on the current branch only). Records completion in `.agents/memory/` so the next
  invocation switches to incremental mode automatically. Use once per repo for the
  initial sweep, then run it on each branch afterward to catch new occurrences in
  changed comments and docs.
---

# Which/that fixer

Fix the common "which/that" confusion in English documentation and code comments.
The error is frequent in code written by Russian speakers, where the Russian
relative pronoun *который* covers both the restrictive ("that") and non-restrictive
("which") English senses indiscriminately.

**Rule:** a relative clause that *restricts or identifies* its antecedent uses
"that"; a clause that merely *adds information* about it uses "which", always
preceded by a comma.

| Before                           | After                           | Reason                             |
|----------------------------------|---------------------------------|------------------------------------|
| `a plugin which forces versions` | `a plugin that forces versions` | restrictive                        |
| `a file, which is generated`     | `a file, which is generated`    | non-restrictive — leave alone      |
| `in which case`                  | `in which case`                 | prepositional phrase — leave alone |
| `Which plugin should I use?`     | `Which plugin should I use?`    | interrogative — leave alone        |

## Workflow

1. **Detect mode.**
   - Read `.agents/memory/which-fixer-applied.md` if it exists.
   - Absent → **bulk mode**: scan every project-owned file in the repository
     (step 2 defines what "project-owned" excludes).
   - Present → **incremental mode**: scan only the files changed on the current
     branch, *including uncommitted edits* — agents in this repo often work
     before an explicit commit, so a committed-only diff would miss the very
     comments under review. Take the union of:
     - `git diff --name-only --diff-filter=ACMR origin/master...HEAD` — committed
       changes since the branch diverged from `origin/master` (three-dot, not a
       plain tip-to-tip diff); and
     - `git diff --name-only --diff-filter=ACMR HEAD` — staged and unstaged
       working-tree edits.
     `origin/master` is the base ref used across this repo's skills and resolves
     in fresh clones and CI, where a local `master` branch may be absent.
     `--diff-filter=ACMR` excludes deleted paths, so the next step never tries to
     read a file that no longer exists.

2. **Identify target files.**
   Apply this file-type filter in both modes:
   - `**/*.kt`, `**/*.kts`, `**/*.java` — Kotlin and Java sources
   - `**/*.proto` — Protobuf sources (Spine keeps substantial API
     documentation in proto comments, not only file headers)
   - `**/*.md` — Markdown documentation
   - `**/*.adoc` — AsciiDoc (if present)

   Scan **git-tracked files only** — in bulk mode, enumerate candidates with
   `git ls-files` rather than walking the filesystem. Because it lists only
   tracked files, untracked build output, generated sources, and ignored
   artifacts stay out of the set automatically (`git ls-files` filters by
   tracked status, not by `.gitignore`, so a *tracked* generated file is not
   excluded this way); as a safeguard, also drop any `build/` and `.gradle/`
   paths explicitly. In incremental mode, intersect the changed-file list with
   the filter above.

   **Then drop everything the project does not own.** `which-fixer` fixes
   *project-owned* sources only. Editing an upstream file here is worse than a
   no-op: the next `./config/pull` (or submodule update) overwrites the change or
   turns it into a merge conflict, and the same fix is needed again. Skip these
   two kinds of upstream-owned paths in **both** modes:

   - **Submodule contents.** Skip every path declared as a submodule in
     `.gitmodules`, and everything beneath it — the `config` submodule (usually
     `config/`), the shared-agents submodule at `.agents/shared`, and any others
     a repo adds (e.g. `BuildSpeed/`, or example projects mounted under `docs/`).
     In bulk mode `git ls-files` already does this — a submodule appears to the
     parent repo as a single gitlink, not as its files — but apply it explicitly
     so incremental mode, which lists changed *paths*, drops a submodule entry
     the same way.

   - **Files distributed by the `config` repository.** When a repo consumes
     `config` (its `.gitmodules` declares the `config` submodule), `config`'s
     `migrate` step copies shared files *out of* the submodule into the project
     tree, where they become ordinary tracked files — so `git ls-files` and
     `git diff` surface them even though the project does not own them.

     `config` **overwrites** these on every `./config/pull`, so they are always
     config-owned — skip them:
     - `buildSrc/` — the entire Gradle build-logic tree (hundreds of Kotlin
       files with KDoc); by far the largest source of false edits.
       **Exception:** `buildSrc/src/main/kotlin/module.gradle.kts` is
       project-owned — `migrate` saves and restores it, so `./config/pull` never
       overwrites it; scan it. Only that exact file: its `*-module.gradle.kts`
       siblings (e.g. `jvm-module.gradle.kts`) *are* overwritten, so they stay
       skipped.
     - `AGENTS.md`, `CLAUDE.md`, `CODE_OF_CONDUCT.md` — org-wide root docs.
     - `.junie/guidelines.md`, `.github/copilot-instructions.md`, and `.idea/` —
       other docs and IDE settings.

     `config` writes `CONTRIBUTING.md` **only into a repo that lacks one** (an
     "initialize if absent" step), so a repo shipping its own contributor guide
     owns it and `./config/pull` will not overwrite it. Skip `CONTRIBUTING.md`
     only when it is the unmodified org-wide copy — byte-for-byte identical to the
     submodule's `config/CONTRIBUTING.md`. If it differs (or the `config`
     submodule is not checked out, so you cannot confirm), scan it as
     project-owned.

     Apply all of this **only** to repos that consume `config`. The `config` and
     `agents` source repositories declare no `config` submodule, so the rule is
     inert there and their own `AGENTS.md`, `buildSrc/`, etc. are fixed normally
     — correct, since a fix must originate at the source that floats to every
     consumer. The set mirrors what `config`'s `migrate` script copies; if that
     script changes what it distributes, update this step to match. (Do **not**
     instead skip any path that merely exists under the `config/` submodule —
     `config` carries files it does *not* distribute, e.g. its own `README.md`,
     and that would wrongly skip a project's own `README.md`.)

3. **Scan and fix each file.**

   *For `.kt`, `.kts`, `.java`, `.proto` files:* confine scanning to comment
   text only — KDoc (`/** … */`), block comments (`/* … */`), and line
   comments (`//`). Do not alter string literals, identifiers, or any
   executable code token. **Skip code embedded inside doc comments too** —
   `{@code …}` / `{@literal …}` inline tags, `<pre>`/`<code>` HTML blocks,
   `@sample` references, and Markdown backtick spans or fenced blocks inside
   KDoc — so a documented snippet such as `which java` is never rewritten.

   *For `.md` and `.adoc` files:* scan prose and headings only, applying the
   same "do not touch code" discipline so documented samples are never altered.
   Skip every code form, not just the common ones:
   - Markdown — fenced code blocks (triple-backtick and `~~~`), inline code
     spans, and four-space-indented code blocks.
   - AsciiDoc — delimited blocks: listing (`----`), literal (`....`), and
     `[source]` blocks, plus inline code spans.

   Within the scanned text, locate every occurrence of the word "which"
   (case-insensitive). Before replacing, verify **all** of the following:

   - **Comma check (mandatory):** the word "which" is *not* immediately preceded
     by a comma (allowing for optional whitespace between the comma and "which").
     If a comma precedes it, this is non-restrictive — leave it untouched.

   - **No other non-restrictive marker:** likewise skip "which" set off by an
     opening parenthesis or a dash — `(which …`, `— which …`, `– which …`, or
     `-- which …`. Parentheses and dashes introduce a supplementary,
     non-restrictive clause exactly as a comma does, so the word stays "which".

   - **Not a preposition + "which":** skip any "which" immediately preceded by a
     preposition — for example "in which", "of which", "with which", "by which",
     "to which", "at which", "from which", "on which", "for which", "into which",
     "upon which", "under which", "within which", "through which", "against
     which", "without which". A preposition before "which" is always
     grammatically correct and must not be changed.

   - **Not interrogative or determiner:** skip "which" used as a question word
     or determiner, whether in a direct question ("Which plugin…?") or an
     embedded one ("decide which plugin to use", "depending on which mode",
     "no matter which", "which of the following").

   - **Not sentence-initial:** skip "Which" that opens a sentence (capital W
     following `.`, `?`, `!`, or the start of a paragraph/block).

   - **Not part of a hyphenated identifier:** match "which" only as a whole
     word, and skip it when a hyphen abuts it on either side — `which-fixer`,
     `that-which-loop` — because that is a kebab-case name or file name, not the
     relative pronoun. (Without this guard a bulk sweep could rewrite a heading
     or file name such as `which-fixer` to `that-fixer`.)

   - **Not a fixed phrase:** skip the fused relative "that which" (a rewrite
     would produce the nonsensical "that that") and the idiom "which is which".

   Everything that passes all of the above checks is a misused restrictive
   "which". Replace it with "that", matching the original capitalization
   (a restrictive "which" is normally lowercase, since it never opens a sentence).

   Apply the edits in place, file by file. When a file has multiple
   occurrences, batch them into one edit per file rather than one edit per
   occurrence.

   **When uncertain** whether a given "which" is restrictive, leave it unchanged
   and add it to the `Skipped[]` list (see **Report**) with reason "ambiguous".
   A missed case is less harmful than incorrectly changing a non-restrictive
   clause.

4. **Record completion (bulk mode only).**
   Ensure the `.agents/memory/` directory exists (create it if the repo does not
   have one yet), then write `.agents/memory/which-fixer-applied.md`:

   ```markdown
   ---
   name: which-fixer-applied
   description: Records that the which-fixer bulk sweep was completed for this repo.
   metadata:
     type: project
   ---

   Bulk `which-fixer` sweep completed.

   **Why:** Marks the transition from bulk to incremental mode so future
   invocations only scan files modified on the current branch.

   **How to apply:** The `which-fixer` skill reads this file on every
   invocation. When it exists, the skill runs in incremental mode.
   ```

   Then update `.agents/memory/MEMORY.md` with this pointer line — append it if
   the file exists, or create the file with an `# Memory index` heading above the
   pointer if it does not:
   ```
   - [which-fixer applied](which-fixer-applied.md) — bulk sweep done; skill now runs in incremental mode
   ```

5. **Report.**
   Produce the summary specified in the **Report** section below.

## Repo Notes

- The rule is standard English grammar: *Merriam-Webster* and *The Elements of
  Style* (Strunk & White) both state that restrictive relative clauses use
  "that" and non-restrictive ones use "which".
- Prefer a missed case over a wrong fix. If a sentence is ambiguous, note it in
  `Skipped[]` and let a human decide.
- For large repositories, process files directory by directory to stay within
  context limits.

## Report

Return: `Mode` (bulk | incremental), `FilesScanned`, `FilesChanged`,
`Replacements[]` (file, line, before → after), `Skipped[]` (file, line, reason).
